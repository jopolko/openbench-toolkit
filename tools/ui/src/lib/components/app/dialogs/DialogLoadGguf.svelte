<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Loader2 } from '@lucide/svelte';
	import { API_OPENROUTER } from '$lib/constants';
	import { modelProviderStore } from '$lib/stores/model-provider.svelte';

	interface Assessment {
		fit: string;
		arch: string;
		is_moe: boolean;
		quant_label: string;
		active_gb: number;
		total_gb: number;
		kv_cache_gb: number;
		n_ctx_train: number;
		is_split: boolean;
		split_count: number;
		shards_found: number;
		vram_free_gb: number;
		disk_free_gb: number;
		n_layer: number;
		n_head_kv: number;
		head_dim: number;
		sliding_window: number;
		sliding_window_pattern: number;
		n_expert: number;
		n_expert_used: number;
	}

	interface Props {
		open: boolean;
		onLoaded: () => void;
	}

	interface OllamaModel {
		name: string;
		path: string;
		size_gb: number;
		modified_unix: number;
	}

	interface OpenRouterModel {
		id: string;
		name?: string;
		supported_parameters?: string[];
	}

	let { open = $bindable(), onLoaded }: Props = $props();

	let mode = $state<'local' | 'url' | 'ollama' | 'openrouter'>('url');
	let localPath = $state('');
	let remoteUrl = $state('');
	let ollamaModels = $state<OllamaModel[]>([]);
	let ollamaLoading = $state(false);
	let ollamaError = $state('');
	let selectedOllamaModel = $state<OllamaModel | null>(null);
	let openrouterModels = $state<OpenRouterModel[]>([]);
	let openrouterLoading = $state(false);
	let openrouterError = $state('');
	let openrouterFilter = $state('');
	let selectedOpenrouterModel = $state<OpenRouterModel | null>(null);
	let assessing = $state(false);
	let assessment = $state<Assessment | null>(null);
	let assessError = $state('');
	let override = $state(false);
	let proceeding = $state(false);

	const filteredOpenrouterModels = $derived(
		openrouterFilter.trim()
			? openrouterModels.filter((m) =>
					m.id.toLowerCase().includes(openrouterFilter.trim().toLowerCase())
				)
			: openrouterModels
	);

	// Ollama models resolve to a local blob path - from here on they're loaded exactly like a
	// hand-typed local path, just with a friendlier alias attached (see proceed()).
	const source = $derived(
		mode === 'url' ? remoteUrl.trim() : mode === 'ollama' ? (selectedOllamaModel?.path ?? '') : localPath.trim()
	);

	async function loadOllamaModels() {
		ollamaLoading = true;
		ollamaError = '';
		try {
			const resp = await fetch('./model-picker/ollama-models');
			const body = await resp.json().catch(() => ({}));
			if (!resp.ok) throw new Error(body.error || `Request failed (${resp.status})`);
			ollamaModels = (body.models ?? []) as OllamaModel[];
			ollamaModels.sort((a, b) => b.modified_unix - a.modified_unix);
		} catch (e) {
			ollamaError = e instanceof Error ? e.message : String(e);
		} finally {
			ollamaLoading = false;
		}
	}

	async function loadOpenrouterModels() {
		openrouterLoading = true;
		openrouterError = '';
		try {
			const resp = await fetch(API_OPENROUTER.MODELS);
			const body = await resp.json().catch(() => ({}));
			if (!resp.ok) throw new Error(body.error?.message || `Request failed (${resp.status})`);
			openrouterModels = ((body.data ?? []) as OpenRouterModel[]).sort((a, b) =>
				a.id.localeCompare(b.id)
			);
		} catch (e) {
			openrouterError =
				e instanceof Error
					? e.message
					: 'openrouter-proxy sidecar not reachable - is it running (port 8087)?';
		} finally {
			openrouterLoading = false;
		}
	}

	function reset() {
		mode = 'url';
		localPath = '';
		remoteUrl = '';
		ollamaModels = [];
		ollamaError = '';
		selectedOllamaModel = null;
		openrouterModels = [];
		openrouterError = '';
		openrouterFilter = '';
		selectedOpenrouterModel = null;
		assessing = false;
		assessment = null;
		assessError = '';
		override = false;
		proceeding = false;
	}

	function handleOpenChange(newOpen: boolean) {
		open = newOpen;
		if (!newOpen) reset();
	}

	// Ollama is the actual day-to-day source (models get pulled on the Windows host,
	// not hand-fed as URLs/paths) - defaulting to the URL tab meant every open needed
	// an extra click into Ollama, then Rescan, before anything useful showed up. Land
	// straight on Ollama and kick off the scan as soon as the dialog opens, regardless
	// of whether it was opened via handleOpenChange or by the parent flipping the
	// bound `open` prop directly.
	$effect(() => {
		if (open) {
			mode = 'ollama';
			void loadOllamaModels();
		}
	});

	// Any edit to the source invalidates the last assessment - it was for a different file.
	function invalidate() {
		assessment = null;
		assessError = '';
		override = false;
	}

	// The "Local path" tab is the default, so pasting a URL there (rather than switching tabs
	// first) is an easy mistake - it silently gets sent as source=local and fails opaquely
	// ("failed to open GGUF file '<url>' ... No such file or directory"). Catch it here instead.
	function handleLocalInput() {
		if (/^https?:\/\//i.test(localPath.trim())) {
			remoteUrl = localPath.trim();
			localPath = '';
			mode = 'url';
		}
		invalidate();
	}

	async function assess() {
		if (!source || assessing) return;
		assessing = true;
		assessment = null;
		assessError = '';
		override = false;
		try {
			const resp = await fetch('./model-picker/assess-gguf', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(
					mode === 'url' ? { source: 'url', url: source } : { source: 'local', path: source }
				)
			});
			const body = await resp.json().catch(() => ({}));
			if (!resp.ok) {
				throw new Error(body.error || `Request failed (${resp.status})`);
			}
			assessment = body as Assessment;
		} catch (e) {
			assessError = e instanceof Error ? e.message : String(e);
		} finally {
			assessing = false;
		}
	}

	async function proceed() {
		if (mode === 'openrouter') {
			// Nothing to download or load - just point the app at OpenRouter
			// instead of the local router. No llama-server call at all here.
			if (!selectedOpenrouterModel) return;
			modelProviderStore.useOpenRouter(selectedOpenrouterModel.id);
			onLoaded();
			handleOpenChange(false);
			return;
		}

		if (!assessment || proceeding) return;
		if (assessment.fit !== 'fits' && !override) return;
		proceeding = true;
		try {
			await fetch('./model-picker/prepare-download', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					[mode === 'url' ? 'url' : 'path']: source,
					...(mode === 'ollama' && selectedOllamaModel ? { alias: selectedOllamaModel.name } : {}),
					active_gb: assessment.active_gb,
					ctx_size: assessment.n_ctx_train,
					n_layer: assessment.n_layer,
					n_head_kv: assessment.n_head_kv,
					head_dim: assessment.head_dim,
					n_ctx_train: assessment.n_ctx_train,
					sliding_window: assessment.sliding_window,
					sliding_window_pattern: assessment.sliding_window_pattern
				})
			});
			const resp = await fetch('./models', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ model: source, source: mode === 'url' ? 'url' : 'local' })
			});
			if (!resp.ok) {
				const body = await resp.json().catch(() => ({}));
				const message = body.error?.message || body.error || `Request failed (${resp.status})`;
				throw new Error(message);
			}
			// A local GGUF just got loaded - make sure we're not still pointed
			// at OpenRouter from an earlier dialog visit.
			modelProviderStore.useLocal();
			onLoaded();
			handleOpenChange(false);
		} catch (e) {
			assessError = e instanceof Error ? e.message : String(e);
		} finally {
			proceeding = false;
		}
	}

	const fitLabel: Record<string, string> = {
		fits: 'Fits',
		'too-large': 'Too large for this hardware',
		'no-disk-space': 'Not enough free disk space'
	};

	const canProceed = $derived(
		mode === 'openrouter'
			? !!selectedOpenrouterModel
			: !!assessment && !proceeding && (assessment.fit === 'fits' || override)
	);
</script>

<Dialog.Root {open} onOpenChange={handleOpenChange}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Load GGUF</Dialog.Title>
			<Dialog.Description>
				{#if mode === 'openrouter'}
					Pick an OpenRouter model to drive chat instead of a local GGUF - calls go through your
					own OpenRouter API key, configured server-side.
				{:else}
					Point at a GGUF file already on disk, or a direct URL to one, and check whether it fits
					this hardware before downloading or loading it.
				{/if}
			</Dialog.Description>
		</Dialog.Header>

		<div class="flex gap-2">
			<Button
				size="sm"
				variant={mode === 'url' ? 'default' : 'outline'}
				onclick={() => {
					mode = 'url';
					invalidate();
				}}
			>
				Direct URL
			</Button>
			<Button
				size="sm"
				variant={mode === 'local' ? 'default' : 'outline'}
				onclick={() => {
					mode = 'local';
					invalidate();
				}}
			>
				Local path
			</Button>
			<Button
				size="sm"
				variant={mode === 'ollama' ? 'default' : 'outline'}
				onclick={() => {
					mode = 'ollama';
					invalidate();
					void loadOllamaModels();
				}}
			>
				Ollama
			</Button>
			<Button
				size="sm"
				variant={mode === 'openrouter' ? 'default' : 'outline'}
				onclick={() => {
					mode = 'openrouter';
					if (openrouterModels.length === 0) void loadOpenrouterModels();
				}}
			>
				OpenRouter
			</Button>
		</div>

		{#if mode === 'openrouter'}
			<div class="flex flex-col gap-2">
				<div class="flex items-center justify-between">
					<Label>OpenRouter models</Label>
					<Button size="sm" variant="ghost" disabled={openrouterLoading} onclick={loadOpenrouterModels}>
						{#if openrouterLoading}
							<Loader2 class="h-3.5 w-3.5 animate-spin" />
						{/if}
						Rescan
					</Button>
				</div>
				<Input
					bind:value={openrouterFilter}
					placeholder="Filter by model id (e.g. 'qwen', 'gpt-4o')"
				/>
				{#if openrouterError}
					<p class="text-sm text-destructive">{openrouterError}</p>
				{:else if !openrouterLoading && filteredOpenrouterModels.length === 0}
					<p class="text-sm text-muted-foreground">
						{openrouterModels.length === 0
							? 'No models loaded yet.'
							: 'No models match that filter.'}
					</p>
				{:else}
					<div class="flex max-h-60 flex-col gap-1 overflow-y-auto">
						{#each filteredOpenrouterModels as m (m.id)}
							<button
								type="button"
								class="flex items-center justify-between rounded-md border px-2 py-1.5 text-left text-sm hover:bg-accent {selectedOpenrouterModel?.id ===
								m.id
									? 'border-primary bg-accent'
									: 'border-border/50'}"
								onclick={() => (selectedOpenrouterModel = m)}
							>
								<span>{m.name ?? m.id}</span>
								{#if m.supported_parameters && !m.supported_parameters.includes('tools')}
									<span class="text-xs text-muted-foreground">no tool calling</span>
								{/if}
							</button>
						{/each}
					</div>
				{/if}
			</div>
		{:else if mode === 'ollama'}
			<div class="flex flex-col gap-2">
				<div class="flex items-center justify-between">
					<Label>Installed Ollama models</Label>
					<Button size="sm" variant="ghost" disabled={ollamaLoading} onclick={loadOllamaModels}>
						{#if ollamaLoading}
							<Loader2 class="h-3.5 w-3.5 animate-spin" />
						{/if}
						Rescan
					</Button>
				</div>
				{#if ollamaError}
					<p class="text-sm text-destructive">{ollamaError}</p>
				{:else if !ollamaLoading && ollamaModels.length === 0}
					<p class="text-sm text-muted-foreground">
						No Ollama models found (checked $OLLAMA_MODELS / ~/.ollama, and the Windows host's
						profile under WSL).
					</p>
				{:else}
					<div class="flex max-h-48 flex-col gap-1 overflow-y-auto">
						{#each ollamaModels as m (m.path)}
							<button
								type="button"
								class="flex items-center justify-between rounded-md border px-2 py-1.5 text-left text-sm hover:bg-accent {selectedOllamaModel?.path ===
								m.path
									? 'border-primary bg-accent'
									: 'border-border/50'}"
								onclick={() => {
									selectedOllamaModel = m;
									invalidate();
								}}
							>
								<span>{m.name}</span>
								<span class="text-muted-foreground">{m.size_gb.toFixed(1)} GB</span>
							</button>
						{/each}
					</div>
				{/if}
				<Button size="sm" variant="outline" disabled={!source || assessing} onclick={assess}>
					{#if assessing}
						<Loader2 class="h-3.5 w-3.5 animate-spin" />
					{/if}
					Assess
				</Button>
			</div>
		{:else}
			<div class="flex flex-col gap-2">
				<Label for="gguf-source">{mode === 'local' ? 'Path on disk' : 'URL'}</Label>
				{#if mode === 'local'}
					<Input
						id="gguf-source"
						bind:value={localPath}
						oninput={handleLocalInput}
						placeholder="/path/to/model.gguf"
					/>
				{:else}
					<Input
						id="gguf-source"
						bind:value={remoteUrl}
						oninput={invalidate}
						placeholder="https://.../model.gguf"
					/>
				{/if}
				<Button size="sm" variant="outline" disabled={!source || assessing} onclick={assess}>
					{#if assessing}
						<Loader2 class="h-3.5 w-3.5 animate-spin" />
					{/if}
					Assess
				</Button>
			</div>
		{/if}

		{#if assessError}
			<p class="text-sm text-destructive">{assessError}</p>
		{/if}

		{#if assessment}
			<div class="flex flex-col gap-3 rounded-md border border-border/50 p-3 text-sm">
				<div class="flex items-center gap-2">
					<Badge variant={assessment.fit === 'fits' ? 'default' : 'destructive'}>
						{fitLabel[assessment.fit] ?? assessment.fit}
					</Badge>
					<span class="text-muted-foreground">{assessment.arch}</span>
					{#if !assessment.is_moe}
						<Badge variant="destructive">Not MoE</Badge>
					{/if}
					<span class="text-muted-foreground">
						{assessment.is_moe
							? `MoE (${assessment.n_expert_used}/${assessment.n_expert} experts)`
							: 'Dense'}
					</span>
					<span class="text-muted-foreground">{assessment.quant_label}</span>
				</div>
				{#if assessment.is_split}
					<p class="text-xs text-muted-foreground">
						{assessment.shards_found === assessment.split_count
							? `Split GGUF - size aggregated from all ${assessment.split_count} shards.`
							: `Split GGUF - only found ${assessment.shards_found}/${assessment.split_count} shards, size estimate is incomplete.`}
					</p>
				{/if}
				<div class="grid grid-cols-2 gap-x-4 gap-y-1 tabular-nums">
					<span class="text-muted-foreground">Active VRAM</span>
					<span>{assessment.active_gb.toFixed(1)} GB</span>
					<span class="text-muted-foreground">Total size</span>
					<span>{assessment.total_gb.toFixed(1)} GB</span>
					<span class="text-muted-foreground">KV cache</span>
					<span>{assessment.kv_cache_gb.toFixed(1)} GB</span>
					<span class="text-muted-foreground">Context (train)</span>
					<span>{assessment.n_ctx_train.toLocaleString()}</span>
					<span class="text-muted-foreground">VRAM free</span>
					<span>{assessment.vram_free_gb.toFixed(1)} GB</span>
					<span class="text-muted-foreground">Disk free</span>
					<span>{assessment.disk_free_gb.toFixed(1)} GB</span>
				</div>
				{#if assessment.fit !== 'fits'}
					<div class="flex items-center gap-2">
						<Checkbox id="gguf-override" bind:checked={override} />
						<Label for="gguf-override" class="text-xs font-normal">
							Override and proceed anyway
						</Label>
					</div>
				{/if}
			</div>
		{/if}

		<Dialog.Footer>
			<Button variant="outline" onclick={() => handleOpenChange(false)}>Cancel</Button>
			<Button disabled={!canProceed} onclick={proceed}>
				{#if proceeding}
					<Loader2 class="h-3.5 w-3.5 animate-spin" />
				{/if}
				Proceed
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
