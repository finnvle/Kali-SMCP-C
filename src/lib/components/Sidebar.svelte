<script lang="ts">
	import type { Session } from '$lib/types';

	interface Props {
		sessions: Session[];
		currentSessionId: string;
		editingSessionId: string | null;
		tempSessionTitle: string;
		onSelectSession: (id: string) => void;
		onCreateSession: () => void;
		onDeleteSession: (id: string) => void;
		onStartEditing: (session: Session) => void;
		onUpdateTitle: () => void;
		onCancelEditing: () => void;
		onTempTitleChange: (value: string) => void;
	}

	let {
		sessions,
		currentSessionId,
		editingSessionId,
		tempSessionTitle,
		onSelectSession,
		onCreateSession,
		onDeleteSession,
		onStartEditing,
		onUpdateTitle,
		onCancelEditing,
		onTempTitleChange
	}: Props = $props();
</script>

<aside class="flex w-64 shrink-0 flex-col border-r border-theme-border bg-theme-bg-panel">
	<!-- Brand -->
	<div class="flex items-center gap-2.5 border-b border-theme-border px-4 py-4">
		<div
			class="flex h-8 w-8 items-center justify-center rounded bg-theme-primary/15 text-theme-primary ring-1 ring-theme-primary/30"
		>
			<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
				><path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
				/></svg
			>
		</div>
		<div>
			<h1 class="font-mono text-sm font-bold text-slate-100">
				<span class="text-theme-primary">KALI</span> SMCP-C
			</h1>
			<p class="font-mono text-[9px] tracking-wider text-slate-500 uppercase">by FINNVLE</p>
		</div>
	</div>

	<!-- Session List Header -->
	<div class="flex items-center justify-between px-4 pt-4 pb-2">
		<h2 class="font-mono text-[10px] font-bold tracking-widest text-slate-500 uppercase">Tasks</h2>
		<button
			onclick={onCreateSession}
			class="flex h-6 w-18 items-center justify-center rounded bg-theme-primary/15 font-mono text-[10px] font-bold text-theme-primary ring-1 ring-theme-primary/30 transition-all hover:bg-theme-primary hover:text-theme-bg"
			title="New Operation"
			aria-label="New Operation"
		>
			<span class="leading-none">+ New Chat</span>
		</button>
	</div>

	<!-- Session List -->
	<div class="scrollbar-thin flex-1 space-y-0.5 overflow-y-auto px-3 pb-3">
		{#each sessions as session (session.id)}
			<div
				role="button"
				tabindex="0"
				onclick={() => onSelectSession(session.id)}
				onkeydown={(e) => {
					if (e.key === 'Enter') onSelectSession(session.id);
				}}
				class="group flex w-full cursor-pointer items-center gap-2 rounded px-2.5 py-2 text-left font-mono text-xs transition-all {currentSessionId ===
				session.id
					? 'bg-theme-primary-light text-theme-primary ring-1 ring-theme-primary/40'
					: 'text-slate-400 hover:bg-theme-border/50 hover:text-slate-200'}"
			>
				<svg
					class="h-3 w-3 shrink-0 opacity-50"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
					stroke-width="2"
					><path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z"
					/></svg
				>
				{#if editingSessionId === session.id}
					<input
						type="text"
						value={tempSessionTitle}
						oninput={(e) => onTempTitleChange(e.currentTarget.value)}
						onblur={onUpdateTitle}
						onkeydown={(e) => {
							if (e.key === 'Enter') onUpdateTitle();
							if (e.key === 'Escape') onCancelEditing();
						}}
						class="w-full flex-1 border-b border-theme-primary bg-transparent py-0.5 outline-none"
						autofocus
					/>
				{:else}
					<span
						role="button"
						tabindex="0"
						ondblclick={() => onStartEditing(session)}
						onkeydown={(e) => {
							if (e.key === 'Enter') onStartEditing(session);
						}}
						class="flex-1 truncate focus:outline-none"
					>
						{session.title}
					</span>
				{/if}

				{#if session.is_active}
					<div class="flex items-center gap-1.5 px-1">
						<span class="relative flex h-1.5 w-1.5">
							<span
								class="absolute inline-flex h-full w-full animate-ping rounded-full bg-theme-primary opacity-75"
							></span>
							<span class="relative inline-flex h-1.5 w-1.5 rounded-full bg-theme-primary"></span>
						</span>
					</div>
				{/if}

				<!-- Action Buttons (Hover or Editing) -->
				<div
					class="flex items-center gap-0.5 {editingSessionId === session.id
						? 'opacity-100'
						: 'opacity-0 transition-opacity group-hover:opacity-100'}"
				>
					{#if editingSessionId === session.id}
						<!-- Checkmark (Save) -->
						<button
							onmousedown={(e) => e.preventDefault()}
							onclick={(e) => {
								e.stopPropagation();
								onUpdateTitle();
							}}
							class="flex h-5 w-5 items-center justify-center rounded text-theme-primary transition-colors hover:bg-theme-primary/20"
							title="Save"
							aria-label="Save title"
						>
							<svg
								class="h-4 w-4"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2.5"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<polyline points="20 6 9 17 4 12"></polyline>
							</svg>
						</button>
					{:else}
						<!-- Pencil (Rename) -->
						<button
							onclick={(e) => {
								e.stopPropagation();
								onStartEditing(session);
							}}
							class="flex h-5 w-5 items-center justify-center rounded text-slate-500 transition-colors hover:bg-theme-primary/20 hover:text-theme-primary"
							title="Rename"
							aria-label="Rename session"
						>
							<svg
								class="h-3 w-3"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
								<path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
							</svg>
						</button>
					{/if}

					<button
						onclick={(e) => {
							e.stopPropagation();
							onDeleteSession(session.id);
						}}
						class="flex h-5 w-5 items-center justify-center rounded text-slate-500 transition-colors hover:bg-red-900/50 hover:text-red-400"
						title="Delete"
						aria-label="Delete session"
					>
						<svg
							class="h-3 w-3"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg
						>
					</button>
				</div>
			</div>
		{/each}
	</div>
</aside>
