<script lang="ts">
	import type { AppConfig } from '$lib/types';

	interface Props {
		inputText: string;
		isGenerating: boolean;
		statusText: string;
		appConfig: AppConfig | null;
		onSend: () => void;
		onInputChange: (value: string) => void;
	}

	let { inputText, isGenerating, statusText, appConfig, onSend, onInputChange }: Props = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			onSend();
		}
	}
</script>

<footer class="z-10 shrink-0 border-t border-theme-border bg-theme-bg-panel/95 p-4 backdrop-blur">
	<div class="mx-auto max-w-4xl">
		{#if statusText}
			<div
				class="mb-2 ml-1 animate-pulse font-mono text-[10px] font-bold tracking-wider text-theme-primary uppercase"
			>
				[*] {statusText}
			</div>
		{/if}
		<div
			class="relative flex items-center rounded border border-theme-border bg-theme-bg shadow-inner transition-all focus-within:border-theme-primary focus-within:ring-1 focus-within:ring-theme-primary/50"
		>
			<textarea
				value={inputText}
				oninput={(e) => onInputChange(e.currentTarget.value)}
				onkeydown={handleKeydown}
				placeholder="$ execute..."
				class="max-h-32 min-h-[44px] w-full resize-none border-0 bg-transparent py-3 pr-12 pl-4 font-mono text-sm text-theme-primary placeholder-slate-600 focus:ring-0"
				rows="1"
				disabled={isGenerating}
			></textarea>

			<button
				onclick={onSend}
				disabled={!inputText.trim() || isGenerating}
				aria-label="Execute command"
				class="absolute right-2 bottom-2 rounded bg-theme-primary px-3 py-1 font-mono text-xs font-bold text-theme-bg transition-all hover:bg-theme-primary-hover hover:shadow-[0_0_8px_rgba(16,185,129,0.6)] disabled:opacity-20 disabled:hover:bg-theme-primary disabled:hover:shadow-none"
			>
				SEND
			</button>
		</div>
		<div
			class="mt-2.5 flex justify-between px-1 font-mono text-[9px] tracking-widest text-slate-600 uppercase"
		>
			{#if appConfig}
				<span>target: {appConfig.mcp_server_url?.replace('http://', '').replace(':5000', '')}</span>
			{:else}
				<span>connecting...</span>
			{/if}
		</div>
	</div>
</footer>
