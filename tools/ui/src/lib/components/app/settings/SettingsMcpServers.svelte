<script lang="ts">
	import { X, Plus } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { mcpStore } from '$lib/stores/mcp.svelte';
	import { conversationsStore } from '$lib/stores/conversations.svelte';
	import { toolsStore } from '$lib/stores/tools.svelte';
	import {
		ActionIcon,
		McpServerCard,
		McpServerCardSkeleton,
		McpServerCardCompact
	} from '$lib/components/app';
	import { DialogMcpServerAddNew } from '$lib/components/app/dialogs';
	import { HealthCheckStatus } from '$lib/enums';
	import { ROUTES, RECOMMENDED_MCP_SERVERS } from '$lib/constants';
	import { fade } from 'svelte/transition';
	import { onMount } from 'svelte';
	import McpLogo from '../mcp/McpLogo.svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import { goto, replaceState } from '$app/navigation';

	// Metasploit's backing stack (msfrpcd, MetasploitMCP, pentest-ui-api) is off
	// by default - same "Enable pentest" action as the /pentest page, but from
	// here it just kicks the launch off and leaves connecting to mcpStore's own
	// reconnect-with-backoff (it'll pick the server up once it's actually up).
	let pentestWarningOpen = $state(false);
	let pendingPentestAction = $state<(() => void) | null>(null);

	function confirmEnablePentest() {
		pentestWarningOpen = false;
		const action = pendingPentestAction;
		pendingPentestAction = null;
		fetch(`${base}/pentest/enable`, { method: 'POST' }).catch(() => {
			// best-effort - if this 403s (server not launched with
			// --enable-pentest-launch) or fails outright, the connect attempt
			// below will surface that as a normal connection error instead
		});
		action?.();
	}

	interface Props {
		class?: string;
	}

	let { class: className }: Props = $props();

	let servers = $derived(mcpStore.visibleMcpServers);

	let addedServerIds = $derived(new Set(servers.map((server) => server.id)));
	let quickAddServers = $derived(
		RECOMMENDED_MCP_SERVERS.filter((server) => !addedServerIds.has(server.id))
	);

	let initialLoadComplete = $state(false);
	let isAddingServer = $state(false);

	function handleQuickAdd(server: (typeof RECOMMENDED_MCP_SERVERS)[number]) {
		if (server.id === 'metasploit-mcp') {
			pendingPentestAction = () => quickAddServer(server);
			pentestWarningOpen = true;
			return;
		}
		quickAddServer(server);
	}

	function quickAddServer(server: (typeof RECOMMENDED_MCP_SERVERS)[number]) {
		const existing = mcpStore.getServerById(server.id);
		if (existing) {
			mcpStore.updateServer(server.id, { enabled: true });
		} else {
			mcpStore.addServer({
				id: server.id,
				enabled: true,
				url: server.url,
				name: server.name,
				useProxy: server.useProxy
			});
		}
		conversationsStore.setMcpServerOverride(server.id, true);
	}

	let previousRouteId = $state<string | null>(null);

	$effect(() => {
		const currentId = page.route.id;
		return () => {
			previousRouteId = currentId;
		};
	});

	function handleClose() {
		const prevIsMcpServers = previousRouteId === '/mcp-servers';
		if (browser && window.history.length > 1 && !prevIsMcpServers) {
			history.back();
		} else {
			goto(ROUTES.START);
		}
	}

	onMount(() => {
		if (page.url.searchParams.has('add')) {
			isAddingServer = true;

			const newUrl = new URL(page.url);
			newUrl.searchParams.delete('add');

			replaceState(newUrl, {});
		}
	});

	$effect(() => {
		if (initialLoadComplete) return;

		const allChecked =
			servers.length > 0 &&
			servers.every((server) => {
				const state = mcpStore.getHealthCheckState(server.id);

				return (
					state.status === HealthCheckStatus.SUCCESS || state.status === HealthCheckStatus.ERROR
				);
			});

		if (allChecked) {
			initialLoadComplete = true;
		}
	});
</script>

<div in:fade={{ duration: 150 }}>
	<div class="fixed top-4.5 right-4 z-50 md:hidden">
		<ActionIcon icon={X} tooltip="Close" onclick={handleClose} />
	</div>

	<div
		class="sticky top-0 z-10 mt-4 mb-2 flex items-start gap-4 md:p-4 p-0 px-4 md:justify-between md:px-8"
	>
		<div class="flex items-center gap-2">
			<McpLogo class="h-5 w-5 md:h-6 md:w-6" />

			<h1 class="text-lg font-semibold md:text-2xl">MCP Servers</h1>
		</div>

		<Button
			variant="outline"
			size="lg"
			class="shrink-0 fixed md:static bottom-6 right-6"
			onclick={() => (isAddingServer = true)}
		>
			<Plus class="h-4 w-4" />

			Add New Server
		</Button>
	</div>

	<DialogMcpServerAddNew bind:open={isAddingServer} />

	<div class="grid gap-5 md:space-y-4 {className}">
		{#if servers.length === 0 && !isAddingServer}
			<div class="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
				No MCP Servers configured yet. Add one to enable agentic features.
			</div>
		{/if}

		{#if quickAddServers.length > 0}
			<div class="grid gap-3">
				<h2 class="text-sm font-semibold text-muted-foreground">Quick add</h2>

				<div
					class="grid gap-3"
					style="grid-template-columns: repeat(auto-fill, minmax(min(32rem, calc(100dvw - 2rem)), 1fr));"
				>
					{#each quickAddServers as server (server.id)}
						<McpServerCardCompact
							{server}
							enabled={false}
							onToggle={() => handleQuickAdd(server)}
						/>
					{/each}
				</div>
			</div>
		{/if}

		{#if servers.length > 0}
			<div
				class="grid gap-3"
				style="grid-template-columns: repeat(auto-fill, minmax(min(32rem, calc(100dvw - 2rem)), 1fr));"
			>
				{#each servers as server (server.id)}
					{#if !initialLoadComplete}
						<McpServerCardSkeleton />
					{:else}
						<McpServerCard
							{server}
							enabled={conversationsStore.isMcpServerEnabledForChat(server.id)}
							onToggle={async () => {
								const wasEnabled = conversationsStore.isMcpServerEnabledForChat(server.id);
								const toggle = async () => {
									await conversationsStore.toggleMcpServerForChat(server.id);
									if (!wasEnabled) {
										toolsStore.enableAllToolsForServer(server.id);
									}
								};
								if (!wasEnabled && server.id === 'metasploit-mcp') {
									pendingPentestAction = toggle;
									pentestWarningOpen = true;
									return;
								}
								await toggle();
							}}
							onUpdate={(updates) => mcpStore.updateServer(server.id, updates)}
							onDelete={() => mcpStore.removeServer(server.id)}
						/>
					{/if}
				{/each}
			</div>
		{/if}
	</div>
</div>

<AlertDialog.Root bind:open={pentestWarningOpen}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Confirm enabling pentest</AlertDialog.Title>
			<AlertDialog.Description>
				Connecting Metasploit starts msfrpcd + MetasploitMCP, giving this chat the ability to
				run real exploit modules, generate payloads, and open sessions against whatever target
				you ask it to - not just scanning. Only proceed if you have explicit authorization to
				test that target.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel onclick={() => (pendingPentestAction = null)}>Cancel</AlertDialog.Cancel>
			<AlertDialog.Action
				class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
				onclick={confirmEnablePentest}
			>
				Enable pentest
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
