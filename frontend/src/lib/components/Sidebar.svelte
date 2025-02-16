<script lang="ts">
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { Menu, ChevronLeft, Code, Settings } from 'lucide-svelte';
    import { hasUnsavedChanges } from '$lib/stores/navigation';
    import ConfirmNavigationModal from './ConfirmNavigationModal.svelte';
    import SettingsModal from './SettingsModal.svelte';
    
    let isCollapsed = true;
    let showConfirmModal = false;
    let showSettingsModal = false;
    let pendingNavigation: string | null = null;

    function handleNavigation(href: string) {
        if ($page.url.pathname === '/' && $hasUnsavedChanges) {
            pendingNavigation = href;
            showConfirmModal = true;
        } else {
            goto(href);
        }
    }

    function confirmNavigation() {
        if (pendingNavigation) {
            goto(pendingNavigation);
            showConfirmModal = false;
            pendingNavigation = null;
        }
    }

    function cancelNavigation() {
        showConfirmModal = false;
        pendingNavigation = null;
    }
</script>

<ConfirmNavigationModal 
    show={showConfirmModal}
    onConfirm={confirmNavigation}
    onCancel={cancelNavigation}
/>

<SettingsModal
    show={showSettingsModal}
    onClose={() => showSettingsModal = false}
/>

<aside 
    class:w-[64px]={isCollapsed} 
    class:w-[240px]={!isCollapsed} 
    class="shrink-0 bg-[#1a1a1a] text-white transition-[width] duration-150 ease-out border-r border-[#333333]"
>
    <div class="p-4 flex justify-between items-center border-b border-[#333333]">
        <div class="overflow-hidden whitespace-nowrap">
            {#if !isCollapsed}
                <span class="text-sm font-semibold transition-opacity duration-75">Mako</span>
            {/if}
        </div>
        <button 
            on:click={() => isCollapsed = !isCollapsed}
            class="{isCollapsed ? 'mx-auto' : ''} p-2 hover:bg-[#222222] rounded-lg transition-colors"
        >
            {#if isCollapsed}
                <Menu size={24} />
            {:else}
                <ChevronLeft size={24} />
            {/if}
        </button>
    </div>

    <nav class="p-2">
        <ul class="space-y-2">
            <li>
                <button 
                    on:click={() => handleNavigation('/')}
                    class="w-full flex items-center gap-4 rounded-lg hover:bg-[#222222] transition-colors {$page.url.pathname === '/' ? 'bg-[#222222]' : ''} {isCollapsed ? 'px-2' : 'px-4'} py-3"
                >
                    <Code size={24} class="shrink-0" />
                    <span class="whitespace-nowrap overflow-hidden transition-opacity duration-75 text-sm" class:opacity-0={isCollapsed}>
                        Build
                    </span>
                </button>
            </li>
            <li>
                <button 
                    on:click={() => showSettingsModal = true}
                    class="w-full flex items-center gap-4 rounded-lg hover:bg-[#222222] transition-colors {$page.url.pathname.startsWith('/settings') ? 'bg-[#222222]' : ''} {isCollapsed ? 'px-2' : 'px-4'} py-3"
                >
                    <Settings size={24} class="shrink-0" />
                    <span class="whitespace-nowrap overflow-hidden transition-opacity duration-75 text-sm" class:opacity-0={isCollapsed}>
                        Settings
                    </span>
                </button>
            </li>
        </ul>
    </nav>
</aside> 