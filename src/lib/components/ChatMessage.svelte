<script lang="ts">
	import type { Message } from '$lib/types';
	import { renderMarkdown } from '$lib/markdown';

	interface Props {
		msg: Message;
		index: number;
	}

	let { msg, index }: Props = $props();
</script>

<div
	class="msg-entrance flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}"
	style="animation-delay: {Math.min(index * 30, 300)}ms"
>
	{#if msg.role === 'user'}
		<!-- ── User Message ── -->
		<div class="group relative flex max-w-[80%] items-start gap-3">
			<div
				class="relative flex-1 overflow-hidden rounded-xl rounded-tr-sm border border-theme-primary/25 bg-gradient-to-br from-theme-bg-panel via-theme-bg-panel to-emerald-950/20 px-5 py-4 shadow-[0_2px_20px_rgba(16,185,129,0.06)] transition-shadow duration-300 hover:shadow-[0_2px_24px_rgba(16,185,129,0.12)]"
			>
				<!-- Gradient accent line along right edge -->
				<div
					class="absolute top-0 right-0 h-full w-[2px] bg-gradient-to-b from-theme-primary/60 via-theme-primary/20 to-transparent"
				></div>
				<!-- Corner accents -->
				<div
					class="absolute top-0 right-0 h-3 w-3 rounded-tr-sm border-t-2 border-r-2 border-theme-primary/30"
				></div>
				<div
					class="absolute bottom-0 left-0 h-3 w-3 rounded-bl-xl border-b-2 border-l-2 border-theme-primary/10"
				></div>
				<div class="font-mono text-sm leading-relaxed text-slate-200">
					<span class="mr-1.5 text-theme-primary/50 select-none">❯</span>{msg.content}
				</div>
			</div>
			<!-- User avatar -->
			<div
				class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-theme-primary/10 font-mono text-xs font-bold text-theme-primary shadow-[0_0_10px_rgba(16,185,129,0.1)] ring-1 ring-theme-primary/25"
			>
				$_
			</div>
		</div>
	{:else}
		<!-- ── Assistant Message ── -->
		<div class="group relative flex max-w-[85%] items-start gap-3">
			<!-- Assistant avatar -->
			<div
				class="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-theme-bg-panel shadow-[0_0_12px_rgba(16,185,129,0.08)] ring-1 ring-theme-primary/30"
			>
				<svg
					class="h-4 w-4 text-theme-primary"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
					/>
				</svg>
				<!-- Pulsing status dot -->
				<span class="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5">
					<span
						class="absolute inline-flex h-full w-full animate-ping rounded-full bg-theme-primary opacity-40"
					></span>
					<span
						class="relative inline-flex h-2.5 w-2.5 rounded-full bg-theme-primary shadow-[0_0_6px_rgba(16,185,129,0.8)]"
					></span>
				</span>
			</div>
			<div
				class="relative flex-1 overflow-hidden rounded-xl rounded-tl-sm border border-theme-border/80 bg-theme-bg-panel/70 shadow-[0_2px_16px_rgba(0,0,0,0.25)] backdrop-blur-md"
			>
				<!-- Gradient top accent -->
				<div
					class="absolute top-0 left-0 h-[2px] w-full bg-gradient-to-r from-theme-primary/50 via-theme-primary/15 to-transparent"
				></div>
				<!-- Corner accents -->
				<div
					class="absolute top-0 left-0 h-3 w-3 rounded-tl-sm border-t-2 border-l-2 border-theme-primary/20"
				></div>
				<!-- Subtle scanline effect -->
				<div
					class="pointer-events-none absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(16,185,129,0.015)_2px,rgba(16,185,129,0.015)_4px)]"
				></div>

				<!-- Role label -->
				<div class="flex items-center gap-2 border-b border-theme-border/40 px-5 py-2">
					<span
						class="font-mono text-[10px] font-bold tracking-widest text-theme-primary/70 uppercase"
						>KALI Agent</span
					>
					<span class="h-px flex-1 bg-gradient-to-r from-theme-border/50 to-transparent"></span>
				</div>

				<!-- Content -->
				<div class="relative px-5 py-4">
					{#if msg.content === ''}
						<span class="flex h-6 items-center gap-1.5">
							<span
								class="typing-dot h-2 w-2 rounded-full bg-theme-primary/80"
								style="animation-delay: 0ms"
							></span>
							<span
								class="typing-dot h-2 w-2 rounded-full bg-theme-primary/60"
								style="animation-delay: 150ms"
							></span>
							<span
								class="typing-dot h-2 w-2 rounded-full bg-theme-primary/40"
								style="animation-delay: 300ms"
							></span>
						</span>
					{:else}
						<div
							class="prose prose-sm max-w-none font-sans leading-relaxed text-slate-300 prose-invert prose-headings:text-slate-100 prose-a:text-theme-primary prose-strong:text-slate-100 prose-code:text-theme-primary"
						>
							{@html renderMarkdown(msg.content)}
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
