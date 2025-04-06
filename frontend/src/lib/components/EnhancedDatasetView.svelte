<script lang="ts">
    import DataframeView from './DataframeView.svelte';
    import { onMount } from 'svelte';
    import {fetchApi } from "$lib/utils/api";

    export let datasetPath: string;
    export let datasetName: string;

    let schema: Array<{column: string, type: string}> = [];
    let contextContent: string | null = null;
    let loadingContext = true;

    async function loadContext() {
        if (!datasetPath) {
            contextContent = null;
            loadingContext = false;
            return;
        }

        try {
            loadingContext = true;
            contextContent = null; // Reset content when loading new context
            
            // Extract dataset name from path and remove .parquet extension
            const datasetNameWithoutExt = datasetName.replace('.parquet', '');
            
            // Use the get-dataset-context endpoint
            const response = await fetchApi(`api/get-dataset-context/${datasetNameWithoutExt}`);
            const data = await response.json();
            
            if (!response.ok) {
                console.error('Error loading context:', response.statusText);
                contextContent = null;
                return;
            }

            contextContent = data.exists ? data.content : null;
        } catch (e) {
            console.error('Error loading context:', e);
            contextContent = null;
        } finally {
            loadingContext = false;
        }
    }

    async function loadSchema() {
        try {
            const response = await fetchApi(`api/get-dataset-schema/${datasetName}`);
            const data = await response.json();
            if (data.success) {
                schema = data.schema;
            }
        } catch (error) {
            console.error('Error loading schema:', error);
            schema = [];
        }
    }

    $: {
        if (datasetName) {
            loadSchema();
            loadContext();
        }
    }

    onMount(() => {
        loadSchema();
        loadContext();
    });
</script>

<div class="grid grid-rows-[2fr,auto,1fr] h-full bg-[#111111]">
    <!-- Top section: Dataframe -->
    <div class="overflow-hidden">
        <DataframeView {datasetPath} />
    </div>

    <!-- Middle section: Divider -->
    <div class="h-[6px] bg-[#2A2A2A] border-t border-[#333333]"></div>

    <!-- Bottom section: Schema and Context -->
    <div class="grid grid-cols-2 overflow-hidden" >
        <!-- Schema -->
        <div class="p-4 overflow-auto border-r border-[#333333]">
            <h3 class="text-white text-sm font-semibold mb-4">Dataset Schema</h3>
            <table class="w-full">
                <thead>
                    <tr>
                        <th class="text-left text-gray-400 text-sm font-medium pb-2">Column</th>
                        <th class="text-left text-gray-400 text-sm font-medium pb-2">Type</th>
                    </tr>
                </thead>
                <tbody>
                    {#each schema as {column, type}}
                        <tr>
                            <td class="text-gray-300 text-sm py-1">{column}</td>
                            <td class="text-gray-400 text-sm py-1 font-mono">{type}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        <!-- Context -->
        <div class="p-4 overflow-auto">
            <h3 class="text-white text-sm font-semibold mb-4">Dataset Context</h3>
            {#if loadingContext}
                <div class="text-sm text-gray-400">Loading context...</div>
            {:else if contextContent}
                <div class="prose prose-invert">
                    <pre class="text-gray-300 text-sm whitespace-pre-wrap">{contextContent}</pre>
                </div>
            {:else}
                <div class="text-sm text-gray-400">No context currently</div>
            {/if}
        </div>
    </div>
</div>

<style>
    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #1a1a1a;
    }

    ::-webkit-scrollbar-thumb {
        background: #333333;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #404040;
    }
</style> 