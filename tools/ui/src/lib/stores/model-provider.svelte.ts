/**
 * modelProviderStore - which backend drives chat completions.
 *
 * 'local' (default): the llama-server router, exactly as before - every
 * other store (modelsStore, serverStore, ...) is about this path.
 * 'openrouter': bypass the router entirely and call a user-chosen OpenRouter
 * model through the openrouter-proxy sidecar (see tools/openrouter_proxy.py),
 * which attaches the server-side API key - the browser never holds it.
 *
 * Deliberately separate from modelsStore: OpenRouter models have none of the
 * local load/unload/VRAM lifecycle that store manages, so folding this in
 * would mean faking that lifecycle for a backend that doesn't have one.
 */

import { browser } from '$app/environment';

export type ModelProviderType = 'local' | 'openrouter';

export interface ModelProviderState {
	type: ModelProviderType;
	openrouterModel: string | null;
}

const STORAGE_KEY = 'openbench-model-provider';

function loadFromStorage(): ModelProviderState {
	const fallback: ModelProviderState = { type: 'local', openrouterModel: null };
	if (!browser) return fallback;
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return fallback;
		const parsed = JSON.parse(raw);
		if (parsed?.type === 'openrouter' && typeof parsed.openrouterModel === 'string' && parsed.openrouterModel) {
			return { type: 'openrouter', openrouterModel: parsed.openrouterModel };
		}
	} catch {
		// malformed/cleared storage - fall back to local
	}
	return fallback;
}

class ModelProviderStore {
	state = $state<ModelProviderState>(loadFromStorage());

	get isOpenRouter(): boolean {
		return this.state.type === 'openrouter';
	}

	useLocal(): void {
		this.state = { type: 'local', openrouterModel: null };
		this.persist();
	}

	useOpenRouter(model: string): void {
		this.state = { type: 'openrouter', openrouterModel: model };
		this.persist();
	}

	private persist(): void {
		if (!browser) return;
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
		} catch {
			// best-effort only, same as the rest of this app's localStorage use
		}
	}
}

export const modelProviderStore = new ModelProviderStore();
