<script lang="ts">
    import { page } from '$app/stores';
    import { Menu, X, Code, Settings } from 'lucide-svelte';
    
    let isCollapsed = true;
</script>

<aside 
    class:w-[84px]={isCollapsed} 
    class:w-[315px]={!isCollapsed} 
    class="shrink-0 bg-[#181818] text-white transition-[width] duration-150 ease-out border-r border-[#333333]"
>
    <div class="p-4 flex justify-between items-center border-b border-[#333333]">
        <div class="overflow-hidden whitespace-nowrap">
            {#if !isCollapsed}
                <span class="text-xl font-semibold transition-opacity duration-75">Mako</span>
            {/if}
        </div>
        <button 
            on:click={() => isCollapsed = !isCollapsed}
            class="p-2 hover:bg-[#222222] rounded-lg transition-colors"
        >
            {#if isCollapsed}
                <Menu size={24} />
            {:else}
                <X size={24} />
            {/if}
        </button>
    </div>

    <nav class="p-4">
        <ul class="space-y-4">
            <li>
                <a 
                    href="/" 
                    class="flex items-center gap-4 p-3 rounded-lg hover:bg-[#222222] transition-colors {$page.url.pathname === '/' ? 'bg-[#222222]' : ''}"
                >
                    <Code size={24} class="shrink-0" />
                    <span class="whitespace-nowrap overflow-hidden transition-opacity duration-75" class:opacity-0={isCollapsed}>
                        Build
                    </span>
                </a>
            </li>
            <li>
                <a 
                    href="/data-management" 
                    class="flex items-center gap-4 p-3 rounded-lg hover:bg-[#222222] transition-colors {$page.url.pathname.startsWith('/data-management') ? 'bg-[#222222]' : ''}"
                >
                    <Settings size={24} class="shrink-0" />
                    <span class="whitespace-nowrap overflow-hidden transition-opacity duration-75" class:opacity-0={isCollapsed}>
                        Settings
                    </span>
                </a>
            </li>
        </ul>
    </nav>
</aside> 