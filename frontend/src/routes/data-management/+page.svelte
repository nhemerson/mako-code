# Dependencies
<script lang="ts">
    import { onMount } from 'svelte';

    let dragActive = false;
    let fileInput: HTMLInputElement;
    let selectedFile: File | null = null;
    let newFileName = '';
    let uploadStatus = '';
    let isUploading = false;
    let uploadedData: any[] = [];
    let showData = false;

    const allowedTypes = [
        'application/json',
        'text/csv',
        'application/x-parquet'
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
            !['json', 'csv', 'parquet'].includes(fileExtension || '')) {
            uploadStatus = 'Error: Please upload only JSON, CSV, or Parquet files.';
            return;
        }

        selectedFile = file;
        newFileName = file.name.split('.')[0]; // Default to original filename without extension
        uploadStatus = '';
    };

    const fetchUploadedData = async (filename: string) => {
        try {
            // Make sure we're using the full filename with extension
            const fullFilename = filename.endsWith('.parquet') ? filename : `${filename}.parquet`;
            const response = await fetch(`/api/read-parquet?filename=${fullFilename}`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch data');
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to process data');
            }
            
            uploadedData = data.data;
            showData = true;
        } catch (error: any) {
            console.error('Error fetching data:', error);
            uploadStatus = `Error reading uploaded file: ${error.message}`;
            showData = false;
        }
    };

    const uploadFile = async () => {
        if (!selectedFile || !newFileName) {
            uploadStatus = 'Please select a file and provide a name.';
            return;
        }

        isUploading = true;
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('newFileName', newFileName);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'Upload failed');
            }

            uploadStatus = `File uploaded and converted successfully! Saved to: ${result.path}`;
            // Fetch and display the uploaded data
            await fetchUploadedData(newFileName);  // Use newFileName here
            selectedFile = null;
            newFileName = '';
        } catch (error: any) {
            uploadStatus = `Error: ${error.message}`;
            showData = false;
        } finally {
            isUploading = false;
        }
    };
</script>

<h1>Data Management</h1>

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
        accept=".json,.csv,.parquet"
        class="file-input"
    />
    
    <div class="upload-content">
        {#if !selectedFile}
            <p>Drag and drop your file here or</p>
            <button on:click={() => fileInput.click()}>Browse Files</button>
            <p class="file-types">Accepted file types: JSON, CSV, Parquet</p>
        {:else}
            <div class="selected-file">
                <p>Selected file: {selectedFile.name}</p>
                <div class="rename-section">
                    <label for="newFileName">New file name:</label>
                    <input 
                        type="text" 
                        id="newFileName"
                        bind:value={newFileName}
                        placeholder="Enter new file name"
                    />
                    <span class="extension">.parquet</span>
                </div>
                <div class="button-group">
                    <button 
                        on:click={uploadFile} 
                        disabled={isUploading || !newFileName}
                    >
                        {isUploading ? 'Uploading...' : 'Upload and Convert'}
                    </button>
                    <button 
                        on:click={() => {
                            selectedFile = null;
                            newFileName = '';
                            uploadStatus = '';
                        }}
                    >
                        Cancel
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>

{#if uploadStatus}
    <div class="status-message" class:error={uploadStatus.startsWith('Error')}>
        {uploadStatus}
    </div>
{/if}

{#if showData && uploadedData.length > 0}
    <div class="data-preview">
        <h2>Uploaded Data Preview</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        {#each Object.keys(uploadedData[0]) as header}
                            <th>{header}</th>
                        {/each}
                    </tr>
                </thead>
                <tbody>
                    {#each uploadedData as row}
                        <tr>
                            {#each Object.values(row) as cell}
                                <td>{cell}</td>
                            {/each}
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    </div>
{/if}

<style>
    .upload-container {
        border: 2px dashed #ccc;
        border-radius: 8px;
        padding: 2rem;
        text-align: center;
        margin: 2rem 0;
        transition: all 0.3s ease;
    }

    .dragActive {
        border-color: #4CAF50;
        background-color: rgba(76, 175, 80, 0.1);
    }

    .file-input {
        display: none;
    }

    .upload-content {
        padding: 2rem;
    }

    button {
        padding: 0.5rem 1rem;
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        margin: 0.5rem;
    }

    button:disabled {
        background-color: #cccccc;
        cursor: not-allowed;
    }

    .file-types {
        color: #666;
        font-size: 0.9rem;
        margin-top: 1rem;
    }

    .selected-file {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 4px;
    }

    .rename-section {
        margin: 1rem 0;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }

    .rename-section input {
        padding: 0.5rem;
        border: 1px solid #ccc;
        border-radius: 4px;
    }

    .extension {
        color: #666;
    }

    .button-group {
        display: flex;
        justify-content: center;
        gap: 1rem;
    }

    .status-message {
        margin-top: 1rem;
        padding: 1rem;
        border-radius: 4px;
        background-color: #4CAF50;
        color: white;
    }

    .status-message.error {
        background-color: #f44336;
    }

    .data-preview {
        margin-top: 2rem;
        padding: 1rem;
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .table-container {
        overflow-x: auto;
        margin-top: 1rem;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
    }

    th, td {
        padding: 0.75rem;
        text-align: left;
        border-bottom: 1px solid #eee;
    }

    th {
        background-color: #f5f5f5;
        font-weight: 600;
    }

    tr:hover {
        background-color: #f8f8f8;
    }
</style> 