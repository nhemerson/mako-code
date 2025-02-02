<script lang="ts">
    import { onMount } from 'svelte';
    import { browser } from '$app/environment';
    
    export let value = '';
    export let language = 'javascript';
    export let theme = 'vs-dark';
    
    let Monaco: any;
    let mounted = false;
    let editorLoaded = false;

    onMount(async () => {
        if (!browser) return;
        try {
            // Dynamically import Monaco components only on client side
            const monacoLoader = await import('monaco-editor/esm/vs/editor/editor.api');
            const svelteMonaco = await import('svelte-monaco');
            
            Monaco = monacoLoader.default;
            
            mounted = true;
            editorLoaded = true;
        } catch (error) {
            console.error('Failed to initialize Monaco Editor:', error);
        }

        return () => {
            mounted = false;
            editorLoaded = false;
        };
    });
</script>

{#if browser && mounted && editorLoaded && Monaco}
    <div class="w-full h-[600px] border border-gray-200 rounded-lg overflow-hidden">
        <svelte:component 
            this={Monaco}
            {value}
            {language}
            theme={theme}
            options={{
                automaticLayout: true,
                minimap: { enabled: false },
                fontSize: 14,
                scrollBeyondLastLine: false,
                roundedSelection: false,
                padding: { top: 10 },
                lineNumbers: 'on',
                folding: true,
            }}
            on:change={({ detail }) => {
                value = detail;
            }}
        />
    </div>
{:else}
    <div class="w-full h-[600px] border border-gray-200 rounded-lg overflow-hidden flex items-center justify-center">
        Loading editor...
    </div>
{/if}

<style>
    :global(.monaco-editor) {
        padding-top: 10px;
    }
</style> 