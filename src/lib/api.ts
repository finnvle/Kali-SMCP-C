import type { AppConfig, Message, ModelInfo, Session } from './types';

const API = 'http://localhost:8000';

// ── Backend Health ─────────────────────────────────────
export async function checkBackend(): Promise<boolean> {
    try {
        const res = await fetch(`${API}/app-config`, {
            signal: AbortSignal.timeout(3000)
        });
        return res.ok;
    } catch {
        return false;
    }
}

// ── App Config ─────────────────────────────────────────
export async function fetchAppConfig(): Promise<AppConfig | null> {
    try {
        const res = await fetch(`${API}/app-config`);
        if (res.ok) return await res.json();
    } catch (e) {
        console.error('Failed to load config', e);
    }
    return null;
}

// ── Models ─────────────────────────────────────────────
export interface ModelsResult {
    models: ModelInfo[];
    ollama: boolean;
    claude: boolean;
    openai: boolean;
    gemini: boolean;
}

export async function fetchModels(): Promise<ModelsResult> {
    const result: ModelsResult = {
        models: [],
        ollama: false,
        claude: false,
        openai: false,
        gemini: false
    };

    try {
        const res = await fetch(`${API}/models`);
        if (!res.ok) return result;
        const data = await res.json();

        // Ollama models
        result.ollama = !!data.ollama?.online;
        if (data.ollama?.models) {
            for (const m of data.ollama.models) {
                result.models.push({ id: m, label: m, online: result.ollama, provider: 'ollama' });
            }
        }
        if (result.ollama && result.models.length === 0) {
            result.models.push({ id: 'qwen3:8b', label: 'qwen3:8b', online: true, provider: 'ollama' });
        }

        // Claude
        if (data.claude) {
            result.claude = !!data.claude.online;
            result.models.push({
                id: 'claude',
                label: `Claude (${data.claude.model})`,
                online: result.claude,
                provider: 'claude'
            });
        }

        // OpenAI
        if (data.openai) {
            result.openai = !!data.openai.online;
            result.models.push({
                id: 'openai',
                label: `ChatGPT (${data.openai.model})`,
                online: result.openai,
                provider: 'claude'
            });
        }

        // Gemini
        if (data.gemini) {
            result.gemini = !!data.gemini.online;
            result.models.push({
                id: 'gemini',
                label: `Gemini (${data.gemini.model})`,
                online: result.gemini,
                provider: 'claude'
            });
        }
    } catch (e) {
        console.error('Failed to load models', e);
        result.models = [
            { id: 'qwen3:8b', label: 'qwen3:8b', online: false, provider: 'ollama' },
            { id: 'claude', label: 'Claude', online: false, provider: 'claude' }
        ];
    }

    return result;
}

// ── Sessions ───────────────────────────────────────────
export async function fetchSessions(): Promise<Session[]> {
    const res = await fetch(`${API}/sessions`);
    if (res.ok) return await res.json();
    return [];
}

export async function createSession(id: string, title: string): Promise<void> {
    await fetch(`${API}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, title })
    });
}

export async function deleteSession(id: string): Promise<void> {
    await fetch(`${API}/sessions/${id}`, { method: 'DELETE' });
}

export async function updateSessionTitle(id: string, title: string): Promise<void> {
    await fetch(`${API}/sessions/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title })
    });
}

// ── History ────────────────────────────────────────────
export async function fetchHistory(sessionId: string): Promise<Message[]> {
    const res = await fetch(`${API}/history/${sessionId}`);
    if (res.ok) return await res.json();
    return [];
}

export async function clearHistory(sessionId: string): Promise<void> {
    await fetch(`${API}/history/${sessionId}`, { method: 'DELETE' });
}

// ── Chat / Streaming ──────────────────────────────────
export async function sendChat(
    model: string,
    message: string,
    sessionId: string,
    signal: AbortSignal
): Promise<Response> {
    return fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, message, session_id: sessionId }),
        signal
    });
}

export async function checkActiveStream(
    sessionId: string
): Promise<{ active: boolean }> {
    const res = await fetch(`${API}/chat/active/${sessionId}`);
    return await res.json();
}

export async function getStreamResponse(
    sessionId: string,
    signal: AbortSignal
): Promise<Response> {
    return fetch(`${API}/chat/stream/${sessionId}`, { signal });
}
