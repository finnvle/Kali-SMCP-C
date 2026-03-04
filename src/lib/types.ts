// ── Shared Types ──────────────────────────────────────

export interface ModelInfo {
    id: string;
    label: string;
    online: boolean;
    provider: 'ollama' | 'claude';
}

export interface Message {
    role: string;
    content: string;
}

export interface Session {
    id: string;
    title: string;
    created_at: string;
    is_active?: boolean;
}

export interface AppConfig {
    mcp_server_url: string;
    ollama_base_url: string;
}

export interface ProviderStatus {
    ollama: boolean;
    claude: boolean;
    openai: boolean;
    gemini: boolean;
}
