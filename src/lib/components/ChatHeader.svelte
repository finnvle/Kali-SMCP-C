<script lang="ts">
	import type { ModelInfo } from '$lib/types';

	interface Props {
		backendOnline: boolean | null;
		ollamaOnline: boolean;
		claudeOnline: boolean;
		openaiOnline: boolean;
		geminiOnline: boolean;
		selectedModel: string;
		availableModels: ModelInfo[];
		onModelChange: (model: string) => void;
		onClearHistory: () => void;
	}

	let {
		backendOnline,
		ollamaOnline,
		claudeOnline,
		openaiOnline,
		geminiOnline,
		selectedModel,
		availableModels,
		onModelChange,
		onClearHistory
	}: Props = $props();

	function handleModelSelect(e: Event) {
		const value = (e.target as HTMLSelectElement).value;
		onModelChange(value);
	}
</script>

<header
	class="z-10 flex shrink-0 items-center justify-between border-b border-theme-border bg-theme-bg-panel/80 px-6 py-3 backdrop-blur-sm"
>
	<div class="flex items-center gap-3">
		<svg
			class="h-5 w-5 text-theme-primary"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			><path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4"
			/></svg
		>
		<h1 class="font-mono text-base font-bold text-slate-100">
			<span class="text-theme-primary">KALI</span> SMCP-C
		</h1>

		<!-- Backend status badge -->
		{#if backendOnline === false}
			<span
				class="flex items-center gap-1.5 rounded-full border border-red-500/30 bg-red-500/10 px-2.5 py-0.5 font-mono text-[10px] font-bold tracking-wider text-red-400 uppercase"
			>
				<span class="h-1.5 w-1.5 rounded-full bg-red-400 shadow-[0_0_6px_rgba(239,68,68,0.8)]"
				></span>
				Backend Offline
			</span>
		{:else if backendOnline === true}
			<span
				class="flex items-center gap-1.5 rounded-full border border-theme-primary/30 bg-theme-primary/10 px-2.5 py-0.5 font-mono text-[10px] font-bold tracking-wider text-theme-primary uppercase"
			>
				<span
					class="h-1.5 w-1.5 rounded-full bg-theme-primary shadow-[0_0_6px_rgba(16,185,129,0.8)]"
				></span>
				Backend Connected
			</span>
		{:else}
			<span
				class="flex items-center gap-1.5 rounded-full border border-slate-600/30 bg-slate-600/10 px-2.5 py-0.5 font-mono text-[10px] text-slate-500 uppercase"
			>
				<span class="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500"></span>
				Checking...
			</span>
		{/if}

		<!-- Provider Status Tracker -->
		{#if backendOnline}
			<div class="ml-2 flex items-center gap-2 border-l border-slate-700 pl-4">
				<!-- Ollama Indicator -->
				<div
					class="flex items-center gap-1.5 rounded bg-slate-900/50 px-2 py-0.5 outline outline-1 {ollamaOnline
						? 'outline-theme-primary/20'
						: 'outline-red-500/20'}"
					title="Ollama Local Status"
				>
					<span class="h-1.5 w-1.5 rounded-full {ollamaOnline ? 'bg-theme-primary' : 'bg-red-500'}"
					></span>
					<span class="font-mono text-[10px] text-slate-400">OLLAMA</span>
				</div>

				<!-- Claude Indicator -->
				<div
					class="flex items-center gap-1.5 rounded bg-slate-900/50 px-2 py-0.5 outline outline-1 {claudeOnline
						? 'outline-theme-primary/20'
						: 'outline-red-500/20'}"
					title="Anthropic API Status"
				>
					<span class="h-1.5 w-1.5 rounded-full {claudeOnline ? 'bg-theme-primary' : 'bg-red-500'}"
					></span>
					<span class="font-mono text-[10px] text-slate-400">CLAUDE</span>
				</div>

				<!-- OpenAI Indicator -->
				<div
					class="flex items-center gap-1.5 rounded bg-slate-900/50 px-2 py-0.5 outline outline-1 {openaiOnline
						? 'outline-theme-primary/20'
						: 'outline-red-500/20'}"
					title="OpenAI API Status"
				>
					<span class="h-1.5 w-1.5 rounded-full {openaiOnline ? 'bg-theme-primary' : 'bg-red-500'}"
					></span>
					<span class="font-mono text-[10px] text-slate-400">OPENAI</span>
				</div>

				<!-- Gemini Indicator -->
				<div
					class="flex items-center gap-1.5 rounded bg-slate-900/50 px-2 py-0.5 outline outline-1 {geminiOnline
						? 'outline-theme-primary/20'
						: 'outline-red-500/20'}"
					title="Google Gemini API Status"
				>
					<span class="h-1.5 w-1.5 rounded-full {geminiOnline ? 'bg-theme-primary' : 'bg-red-500'}"
					></span>
					<span class="font-mono text-[10px] text-slate-400">GEMINI</span>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex items-center gap-3">
		<!-- Model Selector with status dots -->
		<div class="relative">
			<select
				value={selectedModel}
				onchange={handleModelSelect}
				class="block w-52 appearance-none rounded border-theme-border bg-theme-bg py-1.5 pr-8 pl-3 font-mono text-xs text-slate-300 transition-colors focus:border-theme-primary focus:ring-1 focus:ring-theme-primary focus:outline-none"
			>
				{#each availableModels as model (model.id)}
					<option value={model.id} disabled={!model.online}>
						{model.online ? '● ' : '○ '}{model.label}{!model.online ? ' (offline)' : ''}
					</option>
				{/each}
			</select>
		</div>

		<button
			onclick={onClearHistory}
			class="rounded px-2.5 py-1.5 font-mono text-[10px] tracking-wider text-slate-500 uppercase transition-colors hover:bg-theme-border hover:text-slate-200"
		>
			Clear
		</button>
	</div>
</header>
