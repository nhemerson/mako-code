<script lang="ts">
    import { fade } from 'svelte/transition';
    import { onMount } from 'svelte';
    
    export let show = false;
    export let onClose: () => void;
    
    // Placeholder settings
    let settings = {
        theme: 'dark',
        fontSize: 12,
        tabSize: 4,
        wordWrap: true,
        showLineNumbers: true,
        autoSave: true
    };

    let isDirty = false;

    function handleSettingChange() {
        isDirty = true;
    }

    async function saveSettings() {
        // TODO: Implement settings save functionality
        isDirty = false;
        onClose();
    }

    onMount(() => {
        // TODO: Load settings from backend/localStorage
    });

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            if (isDirty) {
                if (confirm('You have unsaved changes. Are you sure you want to close?')) {
                    onClose();
                }
            } else {
                onClose();
            }
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
            class="bg-[#222222] rounded-lg p-8 max-w-4xl w-full mx-4 shadow-lg border border-[#333333] max-h-[90vh] overflow-y-auto"
            role="dialog"
            aria-modal="true"
        >
            <div class="flex justify-between items-center mb-8">
                <h1 class="text-2xl font-semibold text-white">Settings</h1>
                <div class="flex items-center gap-4">
                    {#if isDirty}
                        <button
                            on:click={saveSettings}
                            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            Save Changes
                        </button>
                    {/if}
                    <button
                        on:click={onClose}
                        class="text-gray-400 hover:text-white transition-colors"
                        aria-label="Close settings"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
            </div>

            <div class="space-y-8">
                <!-- Editor Settings -->
                <section class="bg-[#1A1A1A] rounded-lg p-6">
                    <h2 class="text-lg font-medium text-white mb-4">Editor Settings</h2>
                    <div class="space-y-4">
                        <div class="flex items-center justify-between">
                            <label for="fontSize" class="text-gray-300">Font Size</label>
                            <input
                                id="fontSize"
                                type="number"
                                bind:value={settings.fontSize}
                                on:change={handleSettingChange}
                                min="8"
                                max="32"
                                class="w-24 px-3 py-2 bg-[#333333] text-white rounded-lg border border-[#444444] focus:outline-none focus:border-blue-500"
                            />
                        </div>

                        <div class="flex items-center justify-between">
                            <label for="tabSize" class="text-gray-300">Tab Size</label>
                            <input
                                id="tabSize"
                                type="number"
                                bind:value={settings.tabSize}
                                on:change={handleSettingChange}
                                min="2"
                                max="8"
                                class="w-24 px-3 py-2 bg-[#333333] text-white rounded-lg border border-[#444444] focus:outline-none focus:border-blue-500"
                            />
                        </div>

                        <div class="flex items-center justify-between">
                            <label for="wordWrap" class="text-gray-300">Word Wrap</label>
                            <input
                                id="wordWrap"
                                type="checkbox"
                                bind:checked={settings.wordWrap}
                                on:change={handleSettingChange}
                                class="w-5 h-5 bg-[#333333] rounded border border-[#444444] checked:bg-blue-600 focus:outline-none"
                            />
                        </div>

                        <div class="flex items-center justify-between">
                            <label for="showLineNumbers" class="text-gray-300">Show Line Numbers</label>
                            <input
                                id="showLineNumbers"
                                type="checkbox"
                                bind:checked={settings.showLineNumbers}
                                on:change={handleSettingChange}
                                class="w-5 h-5 bg-[#333333] rounded border border-[#444444] checked:bg-blue-600 focus:outline-none"
                            />
                        </div>

                        <div class="flex items-center justify-between">
                            <label for="autoSave" class="text-gray-300">Auto Save</label>
                            <input
                                id="autoSave"
                                type="checkbox"
                                bind:checked={settings.autoSave}
                                on:change={handleSettingChange}
                                class="w-5 h-5 bg-[#333333] rounded border border-[#444444] checked:bg-blue-600 focus:outline-none"
                            />
                        </div>
                    </div>
                </section>

                <!-- Theme Settings -->
                <section class="bg-[#1A1A1A] rounded-lg p-6">
                    <h2 class="text-lg font-medium text-white mb-4">Theme Settings</h2>
                    <div class="space-y-4">
                        <div class="flex items-center justify-between">
                            <label for="theme" class="text-gray-300">Theme</label>
                            <select
                                id="theme"
                                bind:value={settings.theme}
                                on:change={handleSettingChange}
                                class="w-48 px-3 py-2 bg-[#333333] text-white rounded-lg border border-[#444444] focus:outline-none focus:border-blue-500"
                            >
                                <option value="dark">Dark</option>
                                <option value="light">Light</option>
                                <option value="system">System</option>
                            </select>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    </div>
{/if}

<style>
    /* Add custom checkbox and select styles */
    input[type="checkbox"] {
        appearance: none;
        -webkit-appearance: none;
        background-color: #333333;
        border: 1px solid #444444;
        border-radius: 4px;
        cursor: pointer;
        position: relative;
    }

    input[type="checkbox"]:checked {
        background-color: #2563eb;
        border-color: #2563eb;
    }

    input[type="checkbox"]:checked::after {
        content: "✓";
        color: white;
        position: absolute;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        font-size: 12px;
    }

    select {
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='white'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 0.5rem center;
        background-size: 1.5em 1.5em;
        padding-right: 2.5rem;
    }
</style> 