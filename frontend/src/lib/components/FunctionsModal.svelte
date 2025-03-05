<script lang="ts">
    import { X } from 'lucide-svelte';

    export let show = false;
    export let onClose: () => void;

    interface UserFunction {
        name: string;
        code: string;
        description: string;
        tags: string[];
        language: string;
        created_at: string;
        updated_at: string;
    }

    let functions: UserFunction[] = [];
    let loading = false;
    let error: string | null = null;

    async function loadFunctions() {
        loading = true;
        error = null;
        try {
            const response = await fetch('http://localhost:8000/api/list-functions');
            const data = await response.json();
            if (data.success) {
                functions = data.functions;
            } else {
                error = data.error || 'Failed to load functions';
                console.error('Failed to load functions:', data.error);
            }
        } catch (err) {
            error = err instanceof Error ? err.message : 'Failed to load functions';
            console.error('Failed to load functions:', err);
        } finally {
            loading = false;
        }
    }

    $: if (show) {
        loadFunctions();
    }
</script>

{#if show}
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-[#1a1a1a] rounded-lg w-[600px] border border-[#333333]">
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b border-[#333333]">
                <h2 class="text-white text-lg font-semibold">User Functions</h2>
                <button 
                    on:click={onClose}
                    class="text-gray-400 hover:text-white transition-colors"
                >
                    <X size={24} />
                </button>
            </div>

            <!-- Content -->
            <div class="p-6">
                {#if loading}
                    <div class="text-center py-8">
                        <p class="text-gray-400">Loading functions...</p>
                    </div>
                {:else if error}
                    <div class="text-center py-8">
                        <p class="text-red-400 mb-2">Error: {error}</p>
                        <button 
                            on:click={loadFunctions}
                            class="text-blue-400 hover:text-blue-300 text-sm"
                        >
                            Try again
                        </button>
                    </div>
                {:else if functions.length === 0}
                    <div class="text-center py-8">
                        <p class="text-gray-400 mb-2">No saved functions yet</p>
                        <p class="text-gray-500 text-sm">
                            Use ⌘/Ctrl + Shift + F to save a function for quick access
                        </p>
                    </div>
                {:else}
                    <div class="space-y-4">
                        {#each functions as func}
                            <div class="border border-[#333333] rounded-lg p-4 hover:bg-[#252525] transition-colors">
                                <div class="flex justify-between items-start mb-2">
                                    <h3 class="text-white font-medium">{func.name}</h3>
                                    <span class="text-xs px-2 py-1 bg-[#333333] rounded text-gray-400">{func.language}</span>
                                </div>
                                {#if func.description}
                                    <p class="text-gray-400 text-sm mb-2">{func.description}</p>
                                {/if}
                                {#if func.tags && func.tags.length > 0}
                                    <div class="flex gap-2">
                                        {#each func.tags as tag}
                                            <span class="text-xs px-2 py-1 bg-[#222222] text-gray-400 rounded">{tag}</span>
                                        {/each}
                                    </div>
                                {/if}
                                <div class="mt-2 text-xs text-gray-500">
                                    Last updated: {new Date(func.updated_at).toLocaleString()}
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if} 