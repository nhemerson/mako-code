<script lang="ts">
    import { page } from '$app/stores';
    import { Menu, X, Home, BarChart3 } from 'lucide-svelte';
    
    let isCollapsed = false;
</script>

<aside class:w-16={isCollapsed} class:w-80={!isCollapsed} class="shrink-0 bg-gray-900 text-white transition-[width] duration-150 ease-out">
    <div class="p-4 flex justify-between items-center border-b border-gray-800">
        <div class="overflow-hidden whitespace-nowrap">
            {#if !isCollapsed}
                <span class="text-xl font-semibold transition-opacity duration-75">Mako</span>
            {/if}
        </div>
        <button 
            on:click={() => isCollapsed = !isCollapsed}
            class="p-2 hover:bg-gray-800 rounded-lg transition-colors"
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
                    class="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-800 transition-colors {$page.url.pathname === '/' ? 'bg-gray-800' : ''}"
                >
                    <Home size={24} class="shrink-0" />
                    <span class="whitespace-nowrap overflow-hidden transition-opacity duration-75" class:opacity-0={isCollapsed}>
                        Home
                    </span>
                </a>
            </li>
            <li>
                <a 
                    href="/data-management" 
                    class="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-800 transition-colors {$page.url.pathname.startsWith('/data-management') ? 'bg-gray-800' : ''}"
                >
                    <BarChart3 size={24} class="shrink-0" />
                    <span class="whitespace-nowrap overflow-hidden transition-opacity duration-75" class:opacity-0={isCollapsed}>
                        Data Management
                    </span>
                </a>
            </li>
        </ul>
    </nav>
</aside> 