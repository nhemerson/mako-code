<script lang="ts">
    import { getApiUrl, fetchApi } from "$lib/utils/api";
    export let datasetPath: string | null;
    let data: any[] = [];
    let columns: string[] = [];
    let loading = true;
    let error: string | null = null;
    let currentPage = 1;
    let rowsPerPage = 100;

    // Helper function to determine if a value is numeric
    function isNumeric(value: any): boolean {
        return !isNaN(value) && value !== null && value !== '';
    }

    // Helper function to format cell content
    function formatCell(value: any): string {
        if (value === null || value === undefined) return '-';
        if (typeof value === 'boolean') return value.toString();
        if (typeof value === 'number') return value.toLocaleString();
        const stringValue = String(value);
        return stringValue.length > 64 ? stringValue.slice(0, 61) + '...' : stringValue;
    }

    async function loadDataset() {
        if (!datasetPath) {
            error = "No dataset path specified";
            loading = false;
            return;
        }

        try {
            loading = true;
            error = null;
            console.log(`Loading dataset from path: ${datasetPath}`);
            
            const response = await fetchApi(`api/dataset?path=${encodeURIComponent(datasetPath)}`);
            const responseText = await response.text();
            
            if (!response.ok) {
                let errorMessage: string;
                try {
                    const errorJson = JSON.parse(responseText);
                    errorMessage = errorJson.detail || 'Unknown error occurred';
                } catch {
                    errorMessage = responseText || `HTTP error! status: ${response.status}`;
                }
                console.error('Failed to load dataset:', errorMessage);
                throw new Error(errorMessage);
            }

            const result = JSON.parse(responseText);
            console.log(`Successfully loaded dataset with ${result.data.length} rows`);
            data = result.data;
            columns = result.columns;
        } catch (e: unknown) {
            const errorMessage = e instanceof Error ? e.message : 'Unknown error occurred';
            error = errorMessage;
            console.error('Error loading dataset:', e);
        } finally {
            loading = false;
        }
    }

    $: {
        if (datasetPath) {
            console.log('Dataset path changed, reloading:', datasetPath);
            loadDataset();
        }
    }

    $: totalPages = Math.ceil(data.length / rowsPerPage);
    $: displayData = data.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);
    $: startRow = (currentPage - 1) * rowsPerPage + 1;
    $: endRow = Math.min(currentPage * rowsPerPage, data.length);

    function nextPage() {
        if (currentPage < totalPages) currentPage++;
    }

    function prevPage() {
        if (currentPage > 1) currentPage--;
    }
</script>

<div class="flex flex-col h-full bg-[#181818] text-white">
    {#if loading}
        <div class="flex items-center justify-center h-full">
            <div class="flex flex-col items-center gap-2">
                <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span class="text-gray-400">Loading dataset...</span>
            </div>
        </div>
    {:else if error}
        <div class="flex items-center justify-center h-full">
            <div class="max-w-lg p-4 bg-red-900/20 rounded-lg">
                <span class="text-red-400 whitespace-pre-wrap">{error}</span>
            </div>
        </div>
    {:else if data.length === 0}
        <div class="flex items-center justify-center h-full">
            <span class="text-gray-400">No data available</span>
        </div>
    {:else}
        <!-- Header with controls -->
        <div class="flex justify-between items-center px-4 py-2 border-b border-t border-[#333333] bg-[#1a1a1a]">
            <div class="text-sm text-gray-400">
                Showing rows {startRow}-{endRow} of {data.length}
            </div>
            <div class="flex items-center gap-2">
                <button 
                    class="px-2 py-1 text-sm bg-[#252525] hover:bg-[#2a2a2a] rounded disabled:opacity-50"
                    disabled={currentPage === 1}
                    on:click={prevPage}
                >
                    Previous
                </button>
                <span class="text-sm text-gray-400">
                    Page {currentPage} of {totalPages}
                </span>
                <button 
                    class="px-2 py-1 text-sm bg-[#252525] hover:bg-[#2a2a2a] rounded disabled:opacity-50"
                    disabled={currentPage === totalPages}
                    on:click={nextPage}
                >
                    Next
                </button>
            </div>
        </div>

        <!-- Table container -->
        <div class="flex-1 overflow-auto">
            <table class="w-full border-collapse">
                <thead class="sticky top-0 z-10 bg-[#242424] shadow-sm">
                    <tr>
                        {#each columns as column}
                            <th class="px-4 py-2 text-left text-xs font-semibold border-b border-r border-[#333333] text-gray-100 last:border-r-0">
                                {column}
                            </th>
                        {/each}
                    </tr>
                </thead>
                <tbody>
                    {#each displayData as row, i}
                        <tr class="hover:bg-[#2a2a2a] {i % 2 === 0 ? 'bg-[#111111]' : 'bg-[#111111]'}">
                            {#each columns as column}
                                {@const value = row[column]}
                                {@const formattedValue = formatCell(value)}
                                <td 
                                    class="px-4 py-2 text-xs border-b border-r border-[#333333] last:border-r-0 max-w-[512px] overflow-hidden {isNumeric(value) ? 'font-mono text-right' : ''}"
                                    style="text-overflow: ellipsis; white-space: nowrap;"
                                    title={String(value)}
                                >
                                    {formattedValue}
                                </td>
                            {/each}
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>

<style>
    /* Custom scrollbar styles */
    :global(.overflow-auto::-webkit-scrollbar) {
        width: 8px;
        height: 8px;
    }

    :global(.overflow-auto::-webkit-scrollbar-track) {
        background: #181818;
    }

    :global(.overflow-auto::-webkit-scrollbar-thumb) {
        background: #333333;
        border-radius: 4px;
    }

    :global(.overflow-auto::-webkit-scrollbar-thumb:hover) {
        background: #444444;
    }
</style> 