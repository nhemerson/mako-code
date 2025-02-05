<script lang="ts">
    import { fade } from 'svelte/transition';
    
    export let show = false;
    export let onConfirm: () => void;
    export let onCancel: () => void;
</script>

{#if show}
    <div 
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        transition:fade
    >
        <div 
            class="bg-[#222222] rounded-lg p-6 max-w-md w-full mx-4 shadow-lg border border-[#333333]"
            role="dialog"
            aria-modal="true"
        >
            <h2 class="text-xl font-semibold text-white mb-4">Leave Build Page?</h2>
            <p class="text-gray-300 mb-6">
                You have unsaved changes. If you leave, your changes will be lost.
            </p>
            <div class="flex justify-end gap-4">
                <button
                    class="px-4 py-2 rounded-lg bg-transparent hover:bg-[#333333] text-white transition-colors"
                    on:click={onCancel}
                >
                    Stay
                </button>
                <button
                    class="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
                    on:click={onConfirm}
                >
                    Leave
                </button>
            </div>
        </div>
    </div>
{/if} 