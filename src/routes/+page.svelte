<script lang="ts">
	import { onMount, tick } from 'svelte';

	// ── Lib imports ────────────────────────────────────────
	import type { ModelInfo, Message, Session, AppConfig } from '$lib/types';
	import * as api from '$lib/api';

	// ── Component imports ──────────────────────────────────
	import Sidebar from '$lib/components/Sidebar.svelte';
	import ChatHeader from '$lib/components/ChatHeader.svelte';
	import ChatMessage from '$lib/components/ChatMessage.svelte';
	import ChatInput from '$lib/components/ChatInput.svelte';

	// ── State ──────────────────────────────────────────────
	let messages = $state<Message[]>([]);
	let sessions = $state<Session[]>([]);
	let currentSessionId = $state('');
	let inputText = $state('');
	let selectedModel = $state('');
	let availableModels = $state<ModelInfo[]>([]);
	let isGenerating = $state(false);
	let statusText = $state('');
	let chatContainer: HTMLElement;
	let appConfig = $state<AppConfig | null>(null);
	let backendOnline = $state<boolean | null>(null);
	let ollamaOnline = $state(false);
	let claudeOnline = $state(false);
	let openaiOnline = $state(false);
	let geminiOnline = $state(false);

	let editingSessionId = $state<string | null>(null);
	let tempSessionTitle = $state('');

	let activeStreamController: AbortController | null = null;

	// ── Lifecycle ─────────────────────────────────────────
	onMount(() => {
		(async () => {
			backendOnline = await api.checkBackend();
			if (backendOnline) {
				await Promise.all([loadSessions(), loadModels(), loadAppConfig()]);
			}
		})();

		const healthInterval = setInterval(async () => {
			const wasOnline = backendOnline;
			backendOnline = await api.checkBackend();
			if (backendOnline) {
				await Promise.all([loadModels(), loadAppConfig()]);
				if (!wasOnline) {
					await loadSessions();
				}
			}
		}, 5000);

		return () => clearInterval(healthInterval);
	});

	// ── Data Loading ──────────────────────────────────────
	async function loadModels() {
		const result = await api.fetchModels();
		availableModels = result.models;
		ollamaOnline = result.ollama;
		claudeOnline = result.claude;
		openaiOnline = result.openai;
		geminiOnline = result.gemini;

		if (!selectedModel || !result.models.find((m) => m.id === selectedModel)) {
			const saved = localStorage.getItem('smcpc_model');
			const savedModel = saved ? result.models.find((m) => m.id === saved && m.online) : null;
			const firstOnline = result.models.find((m) => m.online);
			selectedModel = savedModel?.id || firstOnline?.id || result.models[0]?.id || '';
		}
	}

	async function loadAppConfig() {
		appConfig = await api.fetchAppConfig();
	}

	async function loadSessions() {
		try {
			sessions = await api.fetchSessions();
			if (sessions.length === 0) {
				await handleCreateSession('default', 'New Engagement');
			} else {
				const savedSessionId = localStorage.getItem('smcpc_session_id');
				if (savedSessionId && sessions.find((s) => s.id === savedSessionId)) {
					currentSessionId = savedSessionId;
				} else {
					currentSessionId = sessions[0].id;
				}
				await loadHistory();
				await reconnectStream();
			}
		} catch (e) {
			console.error('Failed to load sessions', e);
		}
	}

	async function loadHistory() {
		if (!currentSessionId) return;
		messages = await api.fetchHistory(currentSessionId);
		await scrollToBottom();
	}

	// ── Session Handlers ──────────────────────────────────
	function selectSession(id: string) {
		if (currentSessionId === id) return;

		if (activeStreamController) {
			activeStreamController.abort();
			activeStreamController = null;
		}

		currentSessionId = id;
		localStorage.setItem('smcpc_session_id', id);
		messages = [];
		isGenerating = false;
		statusText = '';

		(async () => {
			await loadHistory();
			await reconnectStream();
		})();
	}

	async function handleCreateSession(id?: string, title?: string) {
		const newId = id || crypto.randomUUID().slice(0, 8);
		const newTitle = title || `Op ${sessions.length + 1}`;
		try {
			await api.createSession(newId, newTitle);
			sessions = await api.fetchSessions();
			currentSessionId = newId;
			localStorage.setItem('smcpc_session_id', newId);
			await loadHistory();
		} catch (e) {
			console.error('Failed to create session', e);
		}
	}

	async function handleDeleteSession(id: string) {
		try {
			await api.deleteSession(id);
			if (currentSessionId === id) {
				currentSessionId = '';
				messages = [];
			}
			sessions = await api.fetchSessions();
		} catch (e) {
			console.error('Failed to delete session', e);
		}
	}

	function startEditing(session: Session) {
		editingSessionId = session.id;
		tempSessionTitle = session.title;
	}

	async function updateSessionTitle() {
		if (!editingSessionId || !tempSessionTitle.trim()) {
			editingSessionId = null;
			return;
		}
		try {
			await api.updateSessionTitle(editingSessionId, tempSessionTitle.trim());
			sessions = await api.fetchSessions();
		} catch (e) {
			console.error('Failed to update session title', e);
		} finally {
			editingSessionId = null;
		}
	}

	// ── Chat ──────────────────────────────────────────────
	async function handleClearHistory() {
		if (!currentSessionId) return;
		try {
			await api.clearHistory(currentSessionId);
			messages = [];
		} catch (e) {
			console.error('Failed to clear history', e);
		}
	}

	function handleModelChange(model: string) {
		selectedModel = model;
		localStorage.setItem('smcpc_model', model);
	}

	async function sendMessage() {
		if (!inputText.trim() || isGenerating) return;

		isGenerating = true;
		statusText = 'Initializing...';

		const userMsg = inputText.trim();
		messages = [...messages, { role: 'user', content: userMsg }];
		inputText = '';
		await scrollToBottom();

		messages = [...messages, { role: 'assistant', content: '' }];
		const assistantIndex = messages.length - 1;

		activeStreamController = new AbortController();

		try {
			const response = await api.sendChat(
				selectedModel,
				userMsg,
				currentSessionId,
				activeStreamController.signal
			);

			if (!response.body) throw new Error('No response body');
			await processStream(response.body.getReader(), assistantIndex);
		} catch (e: any) {
			if (e.name === 'AbortError') return;
			statusText = `Error: ${e instanceof Error ? e.message : String(e)}`;
		} finally {
			if (activeStreamController?.signal.aborted === false) {
				isGenerating = false;
				statusText = '';
				await scrollToBottom();
			}
		}
	}

	// ── Stream Processing ─────────────────────────────────
	async function reconnectStream() {
		if (!currentSessionId) return;
		try {
			const activeData = await api.checkActiveStream(currentSessionId);

			if (activeData.active) {
				console.log('Reconnecting to active stream...');
				if (activeStreamController) activeStreamController.abort();
				activeStreamController = new AbortController();

				const res = await api.getStreamResponse(currentSessionId, activeStreamController.signal);

				if (res.ok && res.body) {
					isGenerating = true;
					let assistantIdx = -1;
					for (let i = messages.length - 1; i >= 0; i--) {
						if (messages[i].role === 'assistant') {
							assistantIdx = i;
							break;
						}
					}

					if (assistantIdx === -1) {
						messages = [...messages, { role: 'assistant', content: '' }];
						assistantIdx = messages.length - 1;
					}

					await processStream(res.body.getReader(), assistantIdx);
				}
			}
		} catch (e: any) {
			if (e.name === 'AbortError') return;
			console.log('No active stream to reconnect.');
		} finally {
			if (activeStreamController?.signal.aborted === false) {
				isGenerating = false;
				statusText = '';
			}
		}
	}

	async function processStream(
		reader: ReadableStreamDefaultReader<Uint8Array>,
		assistantIndex: number
	) {
		const decoder = new TextDecoder('utf-8');
		let buffer = '';

		try {
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() || '';

				let currentEventType = 'message';

				for (const line of lines) {
					if (line.startsWith('event: ')) {
						currentEventType = line.slice(7).trim();
					} else if (line.startsWith('data: ')) {
						const dataStr = line.slice(6).trim();
						if (!dataStr) continue;

						if (currentEventType === 'status') {
							statusText = dataStr;
						} else if (currentEventType === 'message') {
							try {
								const data = JSON.parse(dataStr);
								if (data.delta) {
									if (messages[assistantIndex].content === 'Consulting the grid...') {
										messages[assistantIndex].content = '';
									}
									messages[assistantIndex].content += data.delta;
									await scrollToBottom();
								}
							} catch (e) {}
						} else if (currentEventType === 'tool_result') {
							try {
								const data = JSON.parse(dataStr);
								const displayCmd = data.cli || data.tool;
								const formattedResult = `\n\n### Command Used:\n\`\`\`bash\n${displayCmd}\n\`\`\`\n\n### Raw Output:\n\`\`\`text\n${data.result}\n\`\`\`\n\n`;
								messages[assistantIndex].content += formattedResult;
								await scrollToBottom();
							} catch (e) {}
						} else if (currentEventType === 'done') {
							return;
						} else if (currentEventType === 'error') {
							statusText = dataStr;
						}
					}
				}
			}
		} catch (e) {
			console.error('Stream processing error:', e);
		}
	}

	// ── Helpers ────────────────────────────────────────────
	async function scrollToBottom() {
		await tick();
		if (chatContainer) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
		}
	}
</script>

<div
	class="flex h-screen w-full bg-theme-bg font-sans text-theme-text-main selection:bg-theme-primary/30"
>
	<!-- ──────── Sidebar ──────── -->
	<Sidebar
		{sessions}
		{currentSessionId}
		{editingSessionId}
		{tempSessionTitle}
		onSelectSession={selectSession}
		onCreateSession={() => handleCreateSession()}
		onDeleteSession={handleDeleteSession}
		onStartEditing={startEditing}
		onUpdateTitle={updateSessionTitle}
		onCancelEditing={() => (editingSessionId = null)}
		onTempTitleChange={(v) => (tempSessionTitle = v)}
	/>

	<!-- ──────── Main ──────── -->
	<div class="relative flex min-w-0 flex-1 flex-col">
		<!-- Header -->
		<ChatHeader
			{backendOnline}
			{ollamaOnline}
			{claudeOnline}
			{openaiOnline}
			{geminiOnline}
			{selectedModel}
			{availableModels}
			onModelChange={handleModelChange}
			onClearHistory={handleClearHistory}
		/>

		<!-- Chat Area -->
		<main class="scrollbar-thin flex-1 overflow-y-auto p-6" bind:this={chatContainer}>
			<div class="mx-auto max-w-4xl space-y-5">
				{#if messages.length === 0}
					<div
						class="mt-24 flex h-full flex-col items-center justify-center space-y-6 font-mono text-sm text-slate-500"
					>
						<div
							class="flex h-16 w-16 items-center justify-center rounded-full bg-theme-primary-light text-theme-primary shadow-[0_0_20px_rgba(16,185,129,0.15)] ring-1 ring-theme-primary/20"
						>
							<svg
								class="h-7 w-7"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								stroke-width="1.5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z"
								/>
							</svg>
						</div>
						<p class="text-slate-400">Awaiting root commands...</p>
					</div>
				{/if}

				{#each messages as msg, i}
					<ChatMessage {msg} index={i} />
				{/each}
			</div>
		</main>

		<!-- Footer -->
		<ChatInput
			{inputText}
			{isGenerating}
			{statusText}
			{appConfig}
			onSend={sendMessage}
			onInputChange={(v) => (inputText = v)}
		/>
	</div>
</div>
