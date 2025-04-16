<script lang="ts">
    import { X, ChevronDown, ChevronUp, Trash2, Edit, Search } from 'lucide-svelte';
    import { fade } from 'svelte/transition';
    import { getApiUrl, fetchApi } from "$lib/utils/api";
    import SaveFunctionModal from './SaveFunctionModal.svelte';

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
    let expandedFunctions = new Set<string>();
    let deletingFunction: string | null = null;
    let showSaveFunctionModal = false;
    let functionToEdit: UserFunction | null = null;
    let searchQuery = '';

    async function loadFunctions() {
        loading = true;
        error = null;
        try {
            const response = await fetchApi('api/list-functions');
            const data = await response.json();
            if (data.success) {
                functions = data.functions;
                console.log('Loaded functions:', functions);
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

    async function deleteFunction(functionName: string) {
        if (!confirm(`Are you sure you want to delete the function "${functionName}"?`)) {
            return;
        }

        deletingFunction = functionName;
        try {
            const response = await fetchApi(`api/delete-function/${functionName}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            
            if (data.success) {
                // Reload the functions list
                await loadFunctions();
            } else {
                error = data.error || 'Failed to delete function';
            }
        } catch (err) {
            error = err instanceof Error ? err.message : 'Failed to delete function';
        } finally {
            deletingFunction = null;
        }
    }

    function editFunction(func: UserFunction) {
        functionToEdit = func;
        showSaveFunctionModal = true;
    }

    function handleSaveFunctionClose() {
        showSaveFunctionModal = false;
        functionToEdit = null;
        loadFunctions(); // Reload the list after saving
    }

    function toggleFunction(functionName: string) {
        if (expandedFunctions.has(functionName)) {
            expandedFunctions.delete(functionName);
        } else {
            expandedFunctions.add(functionName);
        }
        expandedFunctions = expandedFunctions; // Trigger reactivity
    }

    function filterFunctions(functions: UserFunction[], query: string): UserFunction[] {
        if (!query.trim()) return functions;
        
        const searchTerms = query.toLowerCase().split(' ').filter(term => term);
        
        return functions.filter(func => {
            const searchableText = [
                func.name,
                func.description,
                func.code,
                ...(func.tags || []),
                func.language
            ].map(text => (text || '').toLowerCase()).join(' ');
            
            return searchTerms.every(term => searchableText.includes(term));
        });
    }

    $: filteredFunctions = filterFunctions(functions, searchQuery);

    $: if (show) {
        loadFunctions();
        searchQuery = ''; // Reset search query when modal is opened
    }
</script>

{#if show}
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
        transition:fade={{ duration: 0 }}
        on:click|self={onClose} 
    >
        <div class="bg-[#1a1a1a] rounded-lg w-[800px] max-h-[80vh] border border-[#333333] flex flex-col">
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

            <!-- Search Bar -->
            <div class="p-4 border-b border-[#333333]">
                <div class="relative">
                    <input
                        type="text"
                        bind:value={searchQuery}
                        placeholder="Search functions by name, description, tags..."
                        class="w-full bg-[#252525] text-white px-4 py-2 pl-10 rounded-lg border border-[#333333] focus:border-blue-500 focus:outline-none"
                    />
                    <Search size={18} class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                </div>
            </div>

            <!-- Content -->
            <div class="p-6 overflow-y-auto">
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
                {:else if filteredFunctions.length === 0}
                    <div class="text-center py-8">
                        <p class="text-gray-400">No functions match your search</p>
                    </div>
                {:else}
                    <div class="space-y-4">
                        {#each filteredFunctions as func}
                            <div class="border border-[#333333] rounded-lg p-4 hover:bg-[#252525] transition-colors">
                                <div class="flex justify-between items-start mb-2">
                                    <div class="flex-1">
                                        <div class="flex items-center gap-2">
                                            <h3 class="text-white font-medium">{func.name}</h3>
                                            <span class="text-xs px-2 py-1 bg-[#333333] rounded text-gray-400">{func.language}</span>
                                        </div>
                                        {#if func.description}
                                            <p class="text-gray-400 text-sm mt-1">{func.description}</p>
                                        {/if}
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <button 
                                            class="text-gray-400 hover:text-blue-400 transition-colors p-1"
                                            on:click={() => editFunction(func)}
                                        >
                                            <Edit size={20} />
                                        </button>
                                        <button 
                                            class="text-gray-400 hover:text-red-400 transition-colors p-1"
                                            on:click={() => deleteFunction(func.name)}
                                            disabled={deletingFunction === func.name}
                                        >
                                            <Trash2 size={20} />
                                        </button>
                                        <button 
                                            class="text-gray-400 hover:text-white transition-colors p-1"
                                            on:click={() => toggleFunction(func.name)}
                                        >
                                            {#if expandedFunctions.has(func.name)}
                                                <ChevronUp size={20} />
                                            {:else}
                                                <ChevronDown size={20} />
                                            {/if}
                                        </button>
                                    </div>
                                </div>
                                
                                {#if expandedFunctions.has(func.name)}
                                    <div class="mt-4 transition-all" transition:fade={{ duration: 200 }}>
                                        {#if func.code}
                                            <pre class="bg-[#252525] p-4 rounded-lg overflow-x-auto text-sm text-gray-300 font-mono whitespace-pre-wrap">{func.code}</pre>
                                        {:else}
                                            <div class="text-gray-400 text-sm">No code available for this function.</div>
                                        {/if}
                                    </div>
                                {/if}

                                {#if func.tags && func.tags.length > 0}
                                    <div class="flex gap-2 mt-2">
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

{#if showSaveFunctionModal}
    <SaveFunctionModal
        show={true}
        onClose={handleSaveFunctionClose}
        initialFunction={functionToEdit}
    />
{/if} 