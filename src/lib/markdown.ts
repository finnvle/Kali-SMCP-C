import { marked } from 'marked';
import DOMPurify from 'isomorphic-dompurify';
import hljs from 'highlight.js';
import 'highlight.js/styles/atom-one-dark.css';

// ── Custom code renderer ──────────────────────────────
const renderer = new marked.Renderer();
// @ts-ignore
renderer.code = ({ text, lang }: { text: string; lang?: string }) => {
    const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
    const highlighted = hljs.highlight(text, { language }).value;

    return `
		<details class="group my-4 overflow-hidden rounded border border-theme-primary/30 shadow-[0_0_10px_rgba(16,185,129,0.05)]">
			<summary class="flex cursor-pointer select-none items-center gap-2 bg-theme-bg-panel/80 px-4 py-2.5 font-mono text-xs font-bold text-theme-primary transition hover:bg-theme-bg-panel" style="list-style: none;">
				<svg class="h-4 w-4 shrink-0 transform transition-transform group-open:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
				<span class="uppercase tracking-widest text-[10px]">TERMINAL OUTPUT ${lang ? `[${lang}]` : ''}</span>
			</summary>
			<div class="border-t border-theme-primary/30 bg-[#000000] p-4 overflow-x-auto font-mono text-[11px] leading-relaxed text-slate-300">
				<pre><code>${highlighted}</code></pre>
			</div>
		</details>`;
};
marked.use({ renderer });

// ── Public API ────────────────────────────────────────
export function renderMarkdown(content: string): string {
    if (!content) return '';
    try {
        const parsed = marked.parse(content) as string;
        return DOMPurify.sanitize(parsed, {
            ADD_TAGS: ['details', 'summary'],
            ADD_ATTR: [
                'stroke-linecap',
                'stroke-linejoin',
                'stroke-width',
                'stroke',
                'fill',
                'viewBox'
            ],
            USE_PROFILES: { html: true, svg: true }
        });
    } catch (e) {
        return content;
    }
}
