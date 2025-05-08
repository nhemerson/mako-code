<!-- Component for displaying and managing code version history -->
<script lang="ts">
    import { onMount, createEventDispatcher } from 'svelte';
    import { fetchApi } from "$lib/utils/api";
    
    export let tabName: string;
    
    const dispatch = createEventDispatcher();
    
    interface Version {
        timestamp: string;
        filename: string;
        execution_success: boolean;
        output_preview: string;
    }
    
    let versions: Version[] = [];
    let loading = false;
    let error = '';
    let expandedVersion: string | null = null;
    
    // Function to clean up old versions
    async function cleanupOldVersions() {
        if (!tabName) return;
        
        try {
            const response = await fetchApi(`api/cleanup-versions/${encodeURIComponent(tabName)}`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (!data.success) {
                console.error('Failed to clean up old versions:', data.message);
            }
        } catch (err) {
            console.error('Error cleaning up old versions:', err);
        }
    }
    
    // Function to check if a version is within the last 24 hours
    function isWithinLast24Hours(timestamp: string): boolean {
        // Parse timestamp in format YYYY-MM-DDTHH-MM-SS
        const [date, time] = timestamp.split('T');
        if (!date || !time) return false;
        const [year, month, day] = date.split('-').map(Number);
        const [hour, minute, second] = time.split('-').map(Number);
        const versionDate = new Date(year, month - 1, day, hour, minute, second);
        const now = new Date();
        const hoursDiff = (now.getTime() - versionDate.getTime()) / (1000 * 60 * 60);
        return hoursDiff <= 24;
    }
    
    // Format timestamp for better display
    function formatTimestamp(timestamp: string): string {
        // Convert from 2024-05-04T11-12-09 format to readable
        const parts = timestamp.replace(/-/g, ':').split('T');
        return `${parts[0]} ${parts[1].replace(/-/g, ':')}`;
    }
    
    // Function to load versions
    async function loadVersions() {
        if (!tabName) return;
        
        loading = true;
        error = '';
        
        try {
            // First clean up old versions
            await cleanupOldVersions();
            
            const response = await fetchApi(`api/list-versions/${encodeURIComponent(tabName)}`);
            const data = await response.json();
            
            if (data.success) {
                // Filter versions to only show those within last 24 hours
                versions = (data.versions || [])
                    .filter((version: Version) => isWithinLast24Hours(version.timestamp))
                    .sort((a: Version, b: Version) => b.timestamp.localeCompare(a.timestamp)); // Sort newest first
            } else {
                error = data.message || 'Failed to load versions';
                versions = [];
            }
        } catch (err) {
            console.error('Error loading versions:', err);
            error = 'Error loading versions';
            versions = [];
        } finally {
            loading = false;
        }
    }
    
    // Function to load a specific version
    async function loadVersion(version: Version) {
        try {
            const response = await fetchApi(`api/get-version/${encodeURIComponent(tabName)}/${encodeURIComponent(version.filename)}`);
            const data = await response.json();
            
            if (data.success && data.code) {
                // Dispatch event to parent component to load this version into editor
                dispatch('loadVersion', { code: data.code, version });
            } else {
                error = data.message || 'Failed to load version code';
            }
        } catch (err) {
            console.error('Error loading version:', err);
            error = 'Error loading version code';
        }
    }
    
    // Toggle expanded view for a version
    function toggleExpand(filename: string) {
        expandedVersion = expandedVersion === filename ? null : filename;
    }
    
    // Update when tab changes
    $: if (tabName) {
        loadVersions();
    }
    
    onMount(() => {
        if (tabName) {
            loadVersions();
        }
    });
</script>

<div class="version-history text-gray-300 p-2 h-full flex flex-col">
    {#if loading}
        <p class="text-gray-400 text-xs">Loading versions...</p>
    {:else if error}
        <p class="text-red-400 text-xs">{error}</p>
    {:else if versions.length === 0}
        <p class="text-gray-400 text-xs">No versions found for this file.</p>
        <p class="text-gray-400 text-xs mt-2">Run your code to create versions.</p>
    {:else}
        <div class="versions-list space-y-2 flex-1 overflow-y-auto" style="max-height: 40vh;">
            {#each versions as version}
                <div class="version-item p-2 rounded bg-[#222] hover:bg-[#2a2a2a] cursor-pointer text-xs">
                    <div class="flex justify-between items-start" on:click={() => toggleExpand(version.filename)}>
                        <div>
                            <div class="flex items-center">
                                <span class={version.execution_success ? "text-green-400" : "text-red-400"}>●</span>
                                <span class="ml-1">{formatTimestamp(version.timestamp)}</span>
                            </div>
                        </div>
                        <div class="flex">
                            <button 
                                class="text-blue-400 hover:text-blue-300 mr-1 px-2 py-1 text-xs rounded hover:bg-[#333]"
                                on:click|stopPropagation={() => loadVersion(version)}
                            >
                                Load
                            </button>
                            <span class="text-gray-400">{expandedVersion === version.filename ? '▼' : '▶'}</span>
                        </div>
                    </div>
                    
                    {#if expandedVersion === version.filename}
                        <div class="mt-2 p-2 bg-[#1a1a1a] rounded text-gray-400">
                            <div class="text-xs whitespace-pre-line overflow-hidden">
                                {version.output_preview || 'No output'}
                            </div>
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}
    <div class="mt-4">
        <button 
            class="w-full bg-[#333] hover:bg-[#444] text-gray-300 px-2 py-1 rounded text-xs"
            on:click={loadVersions}
        >
            Refresh Versions
        </button>
    </div>
</div>

<style>
    .version-history {
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
    }
    
    .versions-list {
        overflow-y: auto;
    }
    
    /* Custom scrollbar */
    .versions-list::-webkit-scrollbar {
        width: 6px;
    }
    
    .versions-list::-webkit-scrollbar-track {
        background: #1a1a1a;
    }
    
    .versions-list::-webkit-scrollbar-thumb {
        background-color: #333;
        border-radius: 3px;
    }
</style> 