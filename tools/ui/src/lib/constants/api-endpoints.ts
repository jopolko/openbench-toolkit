export const API_MODELS = {
	LIST: '/v1/models',
	LOAD: '/models/load',
	UNLOAD: '/models/unload',
	TUNING: '/models/tuning',
	TUNING_DEFAULTS: '/model-picker/tuning-defaults',
	SSE: '/models/sse'
};

// chat completion routes, the control route drives realtime inference (e.g. end reasoning)
export const API_CHAT = {
	COMPLETIONS: './v1/chat/completions',
	CONTROL: './v1/chat/completions/control'
};

// slot introspection, requires the --slots flag on the server
export const API_SLOTS = {
	LIST: './slots'
};

export const API_TOOLS = {
	LIST: '/tools',
	EXECUTE: '/tools'
};

// resumable stream routes, the conv::model identity is appended as a path segment
export const API_STREAM = {
	BASE: './v1/stream',
	LOOKUP: './v1/streams/lookup'
};

/** CORS proxy endpoint path */
export const CORS_PROXY_ENDPOINT = '/cors-proxy';

/**
 * Base URL for the openrouter-proxy sidecar (tools/openrouter_proxy.py).
 * Separate origin from the llama-server router on purpose - it's a
 * different process so the OpenRouter API key never has to reach the
 * browser or this app's own backend.
 */
export const OPENROUTER_PROXY_BASE_URL = 'http://127.0.0.1:8087';
export const API_OPENROUTER = {
	MODELS: `${OPENROUTER_PROXY_BASE_URL}/v1/models`,
	COMPLETIONS: `${OPENROUTER_PROXY_BASE_URL}/v1/chat/completions`
};
