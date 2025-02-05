<script lang="ts">
    import { fade } from 'svelte/transition';
    
    export let show = false;
    export let onClose: () => void;

    let dragActive = false;
    let fileInput: HTMLInputElement;
    let selectedFile: File | null = null;
    let newFileName = '';
    let uploadStatus = '';
    let isUploading = false;
    let fileExistsConfirmation = false;

    const allowedTypes = [
        'application/json',
        'text/csv',
        'application/x-parquet',
        'application/x-arrow'
    ];

    const handleDrag = (e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            dragActive = true;
        } else if (e.type === "dragleave") {
            dragActive = false;
        }
    };

    const handleDrop = (e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        dragActive = false;

        if (e.dataTransfer?.files && e.dataTransfer.files[0]) {
            handleFiles(e.dataTransfer.files);
        }
    };

    const handleFileInput = (e: Event) => {
        const target = e.target as HTMLInputElement;
        if (target.files) {
            handleFiles(target.files);
        }
    };

    const handleFiles = (files: FileList) => {
        const file = files[0];
        if (!file) return;

        // Check file type
        const fileType = file.type;
        const fileExtension = file.name.split('.').pop()?.toLowerCase();
        
        if (!allowedTypes.includes(fileType) && 
            !['json', 'csv', 'parquet', 'arrow'].includes(fileExtension || '')) {
            uploadStatus = 'Error: Please upload only JSON, CSV, Parquet, or Arrow files.';
            return;
        }

        selectedFile = file;
        // Convert filename to SQL-friendly table name:
        // 1. Get the name without extension
        // 2. Convert to lowercase
        // 3. Replace spaces and special characters with underscores
        // 4. Remove any non-alphanumeric characters except underscores
        newFileName = file.name
            .split('.')[0]
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_+|_+$/g, ''); // Remove leading/trailing underscores
        uploadStatus = '';
    };

    const checkFileExists = async (fileName: string): Promise<boolean> => {
        try {
            const response = await fetch(`http://localhost:8000/api/check-file?filename=${fileName}.parquet`);
            const data = await response.json();
            return data.exists;
        } catch (error) {
            console.error('Error checking file existence:', error);
            return false;
        }
    };

    const uploadFile = async () => {
        if (!selectedFile || !newFileName) {
            uploadStatus = 'Please select a file and provide a name.';
            return;
        }

        // If we're not already in confirmation mode, check if file exists
        if (!fileExistsConfirmation) {
            const exists = await checkFileExists(newFileName);
            if (exists) {
                uploadStatus = `File "${newFileName}.parquet" already exists. Do you want to replace it?`;
                fileExistsConfirmation = true;
                return;
            }
        }

        isUploading = true;
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('newFileName', newFileName);

        try {
            const response = await fetch('http://localhost:8000/api/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Upload failed' }));
                throw new Error(errorData.error || 'Upload failed');
            }

            const result = await response.json();
            
            if (result.success) {
                // Reset the form after successful upload
                resetForm();
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error: any) {
            uploadStatus = `Error: ${error.message}`;
        } finally {
            isUploading = false;
        }
    };

    const resetForm = () => {
        selectedFile = null;
        newFileName = '';
        uploadStatus = '';
        fileExistsConfirmation = false;
    };

    const handleCancel = () => {
        fileExistsConfirmation = false;
        uploadStatus = '';
    };
</script>

{#if show}
    <div 
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        transition:fade
    >
        <div 
            class="bg-[#222222] rounded-lg p-6 max-w-xl w-full mx-4 shadow-lg border border-[#333333]"
            role="dialog"
            aria-modal="true"
        >
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-semibold text-white">Import Data Files</h2>
                <button 
                    class="text-gray-400 hover:text-white text-xl px-2"
                    on:click={() => {
                        resetForm();
                        onClose();
                    }}
                >
                    ×
                </button>
            </div>

            <div 
                class="upload-container"
                class:dragActive
                on:dragenter={handleDrag}
                on:dragleave={handleDrag}
                on:dragover={handleDrag}
                on:drop={handleDrop}
            >
                <input 
                    type="file" 
                    bind:this={fileInput}
                    on:change={handleFileInput}
                    accept=".json,.csv,.parquet,.arrow"
                    class="file-input"
                />
                
                <div class="upload-content">
                    {#if !selectedFile}
                        <p class="text-gray-300">Drag and drop your file here or</p>
                        <button 
                            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                            on:click={() => fileInput.click()}
                        >
                            Browse Files
                        </button>
                        <p class="text-gray-400 text-sm mt-2">Accepted file types: JSON, CSV, Parquet, Arrow</p>
                    {:else}
                        <div class="space-y-6">
                            <!-- File Card -->
                            <div class="bg-[#1a1a1a] rounded-lg p-4 flex items-start gap-4">
                                <div class="text-green-400">
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                        <polyline points="14 2 14 8 20 8"></polyline>
                                        <line x1="16" y1="13" x2="8" y2="13"></line>
                                        <line x1="16" y1="17" x2="8" y2="17"></line>
                                        <polyline points="10 9 9 9 8 9"></polyline>
                                    </svg>
                                </div>
                                <div class="flex-1">
                                    <h3 class="text-white font-medium">{selectedFile.name}</h3>
                                    <div class="flex items-center gap-4 mt-1 text-sm text-gray-400">
                                        <span>{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</span>
                                        <span>{new Date().toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })}</span>
                                        <span class="px-2 py-0.5 bg-white/10 rounded text-xs uppercase">{selectedFile.name.split('.').pop()}</span>
                                    </div>
                                </div>
                                <button 
                                    class="text-gray-400 hover:text-white"
                                    on:click={resetForm}
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <line x1="18" y1="6" x2="6" y2="18"></line>
                                        <line x1="6" y1="6" x2="18" y2="18"></line>
                                    </svg>
                                </button>
                            </div>

                            <!-- Table Name Input -->
                            <div class="space-y-2">
                                <label for="newFileName" class="block text-white font-medium">Table Name</label>
                                <input 
                                    type="text" 
                                    id="newFileName"
                                    bind:value={newFileName}
                                    placeholder="Enter table name"
                                    class="bg-[#333333] text-white border border-[#444444] rounded-lg px-3 py-2 w-full focus:outline-none focus:border-blue-500"
                                />
                                <p class="text-gray-400 text-sm">This name will be used to reference the table in SQL queries</p>
                            </div>

                            <!-- Import Button -->
                            {#if fileExistsConfirmation}
                                <div class="space-y-4">
                                    <button 
                                        class="w-full px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:bg-gray-600 font-medium"
                                        on:click={uploadFile}
                                        disabled={isUploading}
                                    >
                                        {isUploading ? 'Replacing...' : 'Replace File'}
                                    </button>
                                    <button 
                                        class="w-full px-4 py-3 bg-transparent hover:bg-[#333333] text-white rounded-lg transition-colors"
                                        on:click={handleCancel}
                                    >
                                        Cancel
                                    </button>
                                </div>
                            {:else}
                                <button 
                                    class="w-full px-4 py-3 bg-white hover:bg-gray-100 text-black rounded-lg transition-colors disabled:bg-gray-300 disabled:text-gray-500 font-medium flex items-center justify-center gap-2"
                                    on:click={uploadFile} 
                                    disabled={isUploading || !newFileName}
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                        <polyline points="17 8 12 3 7 8"></polyline>
                                        <line x1="12" y1="3" x2="12" y2="15"></line>
                                    </svg>
                                    {isUploading ? 'Importing...' : 'Import 1 File'}
                                </button>
                            {/if}
                        </div>
                    {/if}
                </div>
            </div>

            {#if uploadStatus}
                <div 
                    class="mt-4 p-3 rounded-lg {uploadStatus.startsWith('Error') ? 'bg-red-900/20 text-red-400' : fileExistsConfirmation ? 'bg-yellow-900/20 text-yellow-400' : 'bg-green-900/20 text-green-400'}"
                >
                    {uploadStatus}
                </div>
            {/if}
        </div>
    </div>
{/if}

<style>
    .upload-container {
        border: 2px dashed #444444;
        padding: 2rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        transition: all 0.2s ease;
    }

    .upload-container:hover, .dragActive {
        background-color: rgba(255, 255, 255, 0.03);
        border-color: #666666;
    }

    .file-input {
        display: none;
    }

    .upload-content {
        text-align: center;
    }

    .selected-file {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }
</style> 