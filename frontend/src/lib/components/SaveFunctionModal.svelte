<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';
    
    export let show = false;
    export let onClose: () => void;
    export let initialCode = '';

    let functionName = '';
    let description = '';
    let tags = '';
    let language = 'python';
    let code = initialCode;
    let errorMessage = '';
    let editorContainer: HTMLElement;
    let editor: Monaco.editor.IStandaloneCodeEditor;
    let monaco: typeof Monaco;
    let editorInitialized = false;

    const languages = [
        { id: 'python', name: 'Python' },
        { id: 'sql', name: 'SQL' },
        { id: 'javascript', name: 'JavaScript' }
    ];

    // Initialize Monaco when the component is mounted
    onMount(async () => {
        // Import Monaco
        monaco = await import('monaco-editor');
    });

    // Initialize or update the editor when the modal is shown
    $: if (show && monaco && editorContainer && !editorInitialized) {
        // Wait for the DOM to be ready
        setTimeout(() => {
            try {
                // Create the editor
                editor = monaco.editor.create(editorContainer, {
                    value: initialCode || code,
                    language: 'python',
                    theme: 'vs-dark',
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    lineNumbers: 'on',
                    automaticLayout: true,
                    fontSize: 14,
                    tabSize: 4,
                    renderLineHighlight: 'all',
                    scrollbar: {
                        useShadows: false,
                        verticalScrollbarSize: 10,
                        horizontalScrollbarSize: 10
                    }
                });

                // Update code when editor content changes
                editor.onDidChangeModelContent(() => {
                    code = editor.getValue();
                });

                editorInitialized = true;
                
                // Focus the editor
                editor.focus();
            } catch (error) {
                console.error("Error initializing Monaco editor:", error);
            }
        }, 100);
    }

    // Handle cleanup when modal is closed
    $: if (!show && editorInitialized && editor) {
        editor.dispose();
        editorInitialized = false;
    }

    async function handleSave() {
        try {
            // Get the latest code from the editor if available
            const currentCode = editorInitialized && editor ? editor.getValue() : code;
            
            const response = await fetch('http://localhost:8000/api/save-function', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: functionName,
                    code: currentCode,
                    description,
                    tags: tags.split(',').map(tag => tag.trim()).filter(tag => tag),
                    language
                })
            });

            const result = await response.json();
            
            if (result.success) {
                onClose();
            } else {
                errorMessage = result.error || 'Failed to save function';
            }
        } catch (error) {
            errorMessage = 'Failed to save function. Please try again.';
        }
    }

    // Clear error message when inputs change
    $: {
        functionName;
        code;
        errorMessage = '';
    }

    // Cleanup on component destroy
    onDestroy(() => {
        if (editor) {
            editor.dispose();
        }
    });
</script>

{#if show}
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-[#1a1a1a] rounded-lg w-[750px] max-h-[80vh] overflow-y-auto">
            <div class="p-6">
                <h2 class="text-xl text-white mb-4">Save Function</h2>
                
                {#if errorMessage}
                    <div class="text-red-400 mb-4 p-2 bg-red-900 bg-opacity-20 rounded">
                        {errorMessage}
                    </div>
                {/if}

                <div class="space-y-4">
                    <div>
                        <label class="block text-gray-400 mb-1">Function Name</label>
                        <input
                            type="text"
                            bind:value={functionName}
                            class="w-full bg-[#252525] text-white p-2 rounded border border-[#333333] focus:border-blue-500 focus:outline-none"
                            placeholder="my_function"
                        />
                    </div>

                    <div>
                        <label class="block text-gray-400 mb-1">Code</label>
                        <div 
                            bind:this={editorContainer}
                            class="w-full h-[250px] rounded border border-[#333333] overflow-hidden"
                        ></div>
                    </div>

                    <div>
                        <label class="block text-gray-400 mb-1">Description</label>
                        <textarea
                            bind:value={description}
                            class="w-full bg-[#252525] text-white p-2 rounded border border-[#333333] focus:border-blue-500 focus:outline-none"
                            rows="1"
                            placeholder="Describe what your function does..."
                        ></textarea>
                    </div>

                    <!-- <div>
                        <label class="block text-gray-400 mb-1">Tags (comma-separated)</label>
                        <input
                            type="text"
                            bind:value={tags}
                            class="w-full bg-[#252525] text-white p-2 rounded border border-[#333333] focus:border-blue-500 focus:outline-none"
                            placeholder="data, analysis, helper"
                        />
                    </div> -->

                    <!-- <div>
                        <label class="block text-gray-400 mb-1">Language</label>
                        <select
                            bind:value={language}
                            class="w-full bg-[#252525] text-white p-2 rounded border border-[#333333] focus:border-blue-500 focus:outline-none"
                        >
                            {#each languages as lang}
                                <option value={lang.id}>{lang.name}</option>
                            {/each}
                        </select>
                    </div> -->
                </div>

                <div class="flex justify-end space-x-3 mt-6">
                    <button
                        class="px-4 py-2 text-gray-400 hover:text-white"
                        on:click={onClose}
                    >
                        Cancel
                    </button>
                    <button
                        class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                        on:click={handleSave}
                    >
                        Save Function
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    /* Add custom scrollbar styling */
    :global(.monaco-editor .scrollbar) {
        width: 10px !important;
    }

    :global(.monaco-editor .scrollbar .slider) {
        width: 10px !important;
        border-radius: 5px !important;
    }
</style> 