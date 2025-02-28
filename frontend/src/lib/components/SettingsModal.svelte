<script lang="ts">
    import { fade } from 'svelte/transition';
    
    export let show = false;
    export let onClose: () => void;
    
    const shortcuts = [
        {
            category: "Code Execution",
            items: [
                { keys: ["⌘/Ctrl", "Enter"], description: "Run current file" }
            ]
        },
        {
            category: "Tab Management",
            items: [
                { keys: ["⌘/Ctrl", "Shift", "P"], description: "New Polars file" },
                { keys: ["⌘/Ctrl", "Shift", "L"], description: "New SQL file" },
                { keys: ["⌘/Ctrl", "Shift", "B"], description: "New Bokeh file" },
                { keys: ["⌘/Ctrl", "Shift", "R"], description: "Restore last closed tab" }
            ]
        },
        {
            category: "Navigation",
            items: [
                { keys: ["⌘/Ctrl", "D"], description: "Toggle Data Management sidebar" }
            ]
        },
        {
            category: "Save Functions",
            items: [
                { keys: ["⌘/Ctrl", "S"], description: "Save context file" },
                { keys: ["⌘/Ctrl", "Shift", "F"], description: "Save new function" }
            ]
        }
    ];

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            onClose();
        }
    }
</script>

<svelte:window on:keydown={handleKeydown}/>

{#if show}
    <div 
        class="fixed inset-0 bg-black/90 flex items-center justify-center z-50"
        transition:fade={{ duration: 0 }}
        on:click|self={onClose}
    >
        <div 
            class="bg-[#222222] rounded-lg p-8 max-w-2xl w-full mx-4 shadow-lg border border-[#333333] max-h-[90vh] overflow-y-auto"
            role="dialog"
            aria-modal="true"
        >
            <div class="flex justify-between items-center mb-8">
                <h1 class="text-2xl font-semibold text-white text-xs">Keyboard Shortcuts</h1>
                <button
                    on:click={onClose}
                    class="text-gray-400 hover:text-white transition-colors"
                    aria-label="Close shortcuts"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            <div class="bg-[#1A1A1A] rounded-lg p-6 space-y-8">
                {#each shortcuts as category}
                    <div>
                        <h2 class="text-xs font-medium text-white mb-4">{category.category}</h2>
                        <div class="space-y-4">
                            {#each category.items as shortcut}
                                <div class="flex items-center justify-between text-gray-300 text-xs">
                                    <span>{shortcut.description}</span>
                                    <div class="flex items-center gap-1">
                                        {#each shortcut.keys as key, i}
                                            <kbd class="px-2 py-1 bg-[#333333] rounded border border-[#444444] text-xs">
                                                {key}
                                            </kbd>
                                            {#if i < shortcut.keys.length - 1}
                                                <span class="text-gray-500">+</span>
                                            {/if}
                                        {/each}
                                    </div>
                                </div>
                            {/each}
                        </div>
                    </div>
                {/each}
            </div>
        </div>
    </div>
{/if}
<style>
    kbd {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }
</style> 