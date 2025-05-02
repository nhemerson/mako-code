<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';
	import { setHasUnsavedChanges } from '$lib/stores/navigation';
	import DataImportModal from '$lib/components/DataImportModal.svelte';
	import EnhancedDatasetView from '$lib/components/EnhancedDatasetView.svelte';
	import { closedTabs } from '$lib/stores/editorStore';
	import { codeTemplates } from '$lib/templates/codeTemplates';
	import RightSidebar from '$lib/components/RightSidebar.svelte';
	import SaveFunctionModal from '$lib/components/SaveFunctionModal.svelte';
	import { fetchApi } from "$lib/utils/api";

	let editor: Monaco.editor.IStandaloneCodeEditor;
	let consoleEditor: Monaco.editor.IStandaloneCodeEditor;
	let monaco: typeof Monaco;
	let editorContainer: HTMLElement;
	let consoleContainer: HTMLElement;
	let selectedLanguage: 'python' | 'sql' | 'rust' | 'javascript' = 'python';
	let resizing = false;
	let editorHeight = 'calc(100% - 250px)';
	let output = '';
	let showDataImportModal = false;
	let datasets: Array<{ name: string; path: string }> = [];
	let isExploreExpanded = true;  // New state variable for collapse/expand
	let editingFileName = -1;
	let showDropdownForDataset: string | null = null;  // Track which dataset's dropdown is open
	let isSidebarCollapsed = true;  // New state for sidebar collapse
	let draggedTabIndex: number | null = null;
	let showSaveFunctionModal = false;

	interface EditorFile {
		name: string;
		content: string;
		model?: Monaco.editor.ITextModel;
		type: 'code' | 'dataset' | 'context' | 'home' | 'docs';
		datasetPath: string;
		datasetName?: string;
	}

	let files: EditorFile[] = [
		{
			name: 'Home',
			content: '',
			type: 'home' as const,
			datasetPath: ''
		},
		{ 
			name: 'main.py', 
			content: '# Python example\nprint("Hello World!")', 
			type: 'code' as const,
			datasetPath: '' 
		},
	];
	let activeFileIndex = 0;

	// Save editor state to localStorage
	function saveEditorState() {
		if (editor && files[activeFileIndex]?.type === 'code') {
			// Update current file content before saving
			files[activeFileIndex].content = editor.getValue();
		}
		
		// Create a simplified version of files without Monaco models
		const filesForStorage = files.map(file => ({
			name: file.name,
			content: file.content,
			type: file.type,
			datasetPath: file.datasetPath || '',
			datasetName: file.datasetName
		}));
		
		localStorage.setItem('editorFiles', JSON.stringify(filesForStorage));
		localStorage.setItem('activeFileIndex', activeFileIndex.toString());
		localStorage.setItem('editorHeight', editorHeight);
	}

	// Restore editor state from localStorage
	function restoreEditorState() {
		try {
			const savedFiles = localStorage.getItem('editorFiles');
			const savedActiveIndex = localStorage.getItem('activeFileIndex');
			const savedEditorHeight = localStorage.getItem('editorHeight');
			
			if (savedFiles) {
				const parsedFiles = JSON.parse(savedFiles);
				
				// Check if Home tab exists in saved files
				const hasHomeTab = parsedFiles.some((file: any) => file.type === 'home');
				
				// Map the saved files
				let restoredFiles = parsedFiles.map((file: any) => ({
					...file,
					datasetPath: file.datasetPath || ''
				}));
				
				// If no Home tab, add it as the first tab
				if (!hasHomeTab) {
					restoredFiles = [
						{
							name: 'Home',
							content: '',
							type: 'home' as const,
							datasetPath: ''
						},
						...restoredFiles
					];
				}
				
				files = restoredFiles;
				
				if (savedActiveIndex) {
					// If we added a Home tab and it wasn't there before, adjust the active index
					const activeIdx = parseInt(savedActiveIndex, 10);
					activeFileIndex = hasHomeTab ? activeIdx : activeIdx + 1;
				}
				if (savedEditorHeight) {
					editorHeight = savedEditorHeight;
				}
				
				// If Monaco is initialized, set up the model for the active file
				if (monaco && editor && files[activeFileIndex]?.type === 'code') {
					const model = monaco.editor.createModel(
						files[activeFileIndex].content,
						'python'
					);
					files[activeFileIndex].model = model;
					editor.setModel(model);
				}
			} else {
				// If no saved state, ensure we have the Home tab
				if (!files.some(file => file.type === 'home')) {
					files = [
						{
							name: 'Home',
							content: '',
							type: 'home' as const,
							datasetPath: ''
						},
						...files
					];
					activeFileIndex = 0;
				}
			}
		} catch (error) {
			console.error('Error restoring editor state:', error);
		}
	}

	function handleDragStart(index: number, event: DragEvent) {
		draggedTabIndex = index;
		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
		}
	}

	function handleDragOver(index: number, event: DragEvent) {
		event.preventDefault();
		if (draggedTabIndex === null || draggedTabIndex === index) return;
		
		const tabElements = document.querySelectorAll('.tab-button');
		const draggedTab = tabElements[draggedTabIndex] as HTMLElement;
		const targetTab = tabElements[index] as HTMLElement;
		
		if (draggedTab && targetTab) {
			const draggedRect = draggedTab.getBoundingClientRect();
			const targetRect = targetTab.getBoundingClientRect();
			
			// Update files array
			const newFiles = [...files];
			const [draggedFile] = newFiles.splice(draggedTabIndex, 1);
			newFiles.splice(index, 0, draggedFile);
			files = newFiles;
			
			// Update active file index
			if (activeFileIndex === draggedTabIndex) {
				activeFileIndex = index;
			} else if (activeFileIndex > draggedTabIndex && activeFileIndex <= index) {
				activeFileIndex--;
			} else if (activeFileIndex < draggedTabIndex && activeFileIndex >= index) {
				activeFileIndex++;
			}
			
			draggedTabIndex = index;
		}
	}

	function handleDragEnd(event: DragEvent) {
		draggedTabIndex = null;
	}

	function addNewFile() {
		const newFileName = `file${files.length + 1}.py`;
		const newFile: EditorFile = { 
			name: newFileName, 
			content: '# New file', 
			type: 'code' as const,
			datasetPath: '' 
		};
		files = [...files, newFile];
		activeFileIndex = files.length - 1;
		
		if (monaco && editor) {
			const model = monaco.editor.createModel(
				files[activeFileIndex].content,
				'python'
			);
			files[activeFileIndex].model = model;
			editor.setModel(files[activeFileIndex].model || null);
		}
	}

	function switchFile(index: number) {
		if (index === activeFileIndex) return;
		
		// Save current content if it's a code or context tab
		if ((files[activeFileIndex].type === 'code' || files[activeFileIndex].type === 'context') && editor) {
			files[activeFileIndex].content = editor.getValue();
		}
		
		activeFileIndex = index;
		
		// If switching to a code or context tab
		if (files[activeFileIndex].type === 'code' || files[activeFileIndex].type === 'context') {
			if (!files[activeFileIndex].model) {
				files[activeFileIndex].model = monaco.editor.createModel(
					files[activeFileIndex].content,
					files[activeFileIndex].type === 'context' ? 'markdown' : 'python'
				);
			}
			editor.setModel(files[activeFileIndex].model || null);
			updateEditorTheme();
			
			// Ensure the editor updates its layout
			requestAnimationFrame(() => {
				editor?.layout();
			});
		}
		// If switching to home tab, no need to set up a model
		else if (files[activeFileIndex].type === 'home') {
			// Clear the editor model
			editor.setModel(null);
		}

		// Save state after switching files
		saveEditorState();
	}

	function removeFile(index: number) {
		// Don't allow removing the last file
		if (files.length <= 1) return;

		// Save the file state before removing it
		const fileToClose = files[index];
		closedTabs.addClosedTab({
			name: fileToClose.name,
			content: fileToClose.model ? fileToClose.model.getValue() : fileToClose.content,
			type: fileToClose.type,
			datasetPath: fileToClose.datasetPath,
			datasetName: fileToClose.datasetName
		});

		// Dispose of the model if it exists
		if (files[index].model) {
			files[index].model.dispose();
		}

		// Remove the file
		files = files.filter((_, i) => i !== index);

		// Adjust active file index if needed
		if (index === activeFileIndex) {
			// If we removed the last file, go to the new last file
			activeFileIndex = Math.min(index, files.length - 1);
			if (editor && files[activeFileIndex]) {
				if (!files[activeFileIndex].model) {
					files[activeFileIndex].model = monaco.editor.createModel(
						files[activeFileIndex].content,
						'python'
					);
				}
				editor.setModel(files[activeFileIndex].model || null);
			}
		} else if (index < activeFileIndex) {
			// If we removed a file before the active file, decrement the index
			activeFileIndex--;
		}

		// Save the new state after removing the file
		saveEditorState();
	}

	function changeLanguage() {
		const model = editor.getModel();
		if (model) {
			monaco.editor.setModelLanguage(model, selectedLanguage);
		}
	}

	async function executeCode() {
		const code = editor.getValue();
		consoleEditor.setValue('Running...\n');
		output = ''; // Reset output at start

		try {
			console.log('Executing code:', code.substring(0, 100) + '...');
			
			// Use the API utility to get the correct URL
			const response = await fetchApi('execute', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ code })
			});

			console.log('Response status:', response.status);
			
			const result = await response.json();
			console.log('Response result:', result);
			
			if (result.success) {
				// Handle standard output
				if (result.output && result.output.trim()) {
					output += result.output;
					
					// Check if this was a SQL save operation
					if (code.includes('@sql') && code.includes('save_as:')) {
						await loadDatasets(); // Refresh the datasets list
					}

					// Check if used the mako function to save the output
					if (code.includes('save(')) {
						await loadDatasets(); // Refresh the datasets list
					}

				} else if (result.stdout && result.stdout.trim()) {
					output += result.stdout;
				}
				
				// Handle errors/stderr
				if (result.stderr && result.stderr.trim()) {
					output += '\n\x1b[31m' + result.stderr + '\x1b[0m';
				}
				
				if (!output.trim()) {
					output = '// No output\n';
				}
			} else {
				const errorMsg = '\x1b[31m🔴 Error: ' + (result.error || result.output) + '\x1b[0m';
				output = errorMsg;
			}

			consoleEditor.setValue(output);
			consoleEditor.revealLine(consoleEditor.getModel()?.getLineCount() || 1);
			
			// Save version if this is a code tab
			if (files[activeFileIndex].type === 'code') {
				try {
					await saveCodeVersion(code, files[activeFileIndex].name, result.success, output);
				} catch (versionError) {
					console.error('Failed to save code version:', versionError);
					// Don't disrupt the main flow if version saving fails
				}
			}
		} catch (error: any) {
			console.error('Code execution error:', error);
			const errorMessage = '\x1b[31m🔴 Error: Failed to execute code. Make sure the backend server is running.\n' + error.message + '\x1b[0m';
			consoleEditor.setValue(errorMessage);
			consoleEditor.revealLine(consoleEditor.getModel()?.getLineCount() || 1);
		}
	}

	// Function to save a version of code
	async function saveCodeVersion(code: string, tabName: string, executionSuccess: boolean, output: string) {
		try {
			const response = await fetchApi('api/save-version', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					code,
					tab_name: tabName,
					execution_success: executionSuccess,
					output
				})
			});
			
			const result = await response.json();
			console.log('Version save result:', result);
			
			// Could display a notification here if needed
			
		} catch (error) {
			console.error('Error saving code version:', error);
			// Silent fail - don't disrupt the user's workflow
		}
	}

	function addDatasetTab(name: string, path: string) {
		// Check if a tab for this dataset already exists
		const existingIndex = files.findIndex(f => 
			f.type === 'dataset' && 
			f.datasetPath === path
		);
		if (existingIndex !== -1) {
			// If it exists, switch to it
			activeFileIndex = existingIndex;
			return;
		}

		// Add new tab
		const newFile: EditorFile = { 
			name: name,
			content: '',  // Dataset tabs don't need content
			type: 'dataset' as const,
			datasetPath: path,
			datasetName: name.replace('.parquet', '')
		};
		files = [...files, newFile];
		activeFileIndex = files.length - 1;
	}

	async function loadDatasets() {
		try {
			const response = await fetchApi('api/list-datasets');
			const data = await response.json();
			datasets = data.datasets;
		} catch (error) {
			console.error('Failed to load datasets:', error);
		}
	}

	async function deleteDataset(path: string) {
		try {
			const response = await fetchApi('api/delete-dataset', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ path: path })
			});

			if (response.ok) {
				// Remove the dataset from the list
				datasets = datasets.filter(d => d.path !== path);
				// Close any open tabs for this dataset
				files = files.filter(f => f.type !== 'dataset' || f.datasetPath !== path);
				if (files.length === 0) {
					addNewFile();
				}
				activeFileIndex = 0;
			} else {
				console.error('Failed to delete dataset');
			}
		} catch (error) {
			console.error('Error deleting dataset:', error);
		}
	}

	function analyzeDataset(dataset: { name: string; path: string }) {
		const analysisCode = `import polars as pl

# Read the parquet file
df = pl.read_parquet("./data/local_storage/${dataset.name}.parquet")

# Print the dataframe
print(df)`;

		// Create new file with analysis code
		files = [...files, { 
			name: `analyze_${dataset.name}.py`, 
			content: analysisCode, 
			type: 'code' as const,
			datasetPath: '' 
		}];
		activeFileIndex = files.length - 1;
		
		if (monaco && editor) {
			const model = monaco.editor.createModel(
				files[activeFileIndex].content,
				'python'
			);
			files[activeFileIndex].model = model;
			editor.setModel(files[activeFileIndex].model || null);
		}
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.dataset-dropdown')) {
			showDropdownForDataset = null;
		}
	}

	// Add this new function to handle the keyboard shortcut
	function handleKeyboardShortcut(event: KeyboardEvent) {
		// Check if it's Command+D (Mac) or Ctrl+D (Windows)
		if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'd') {
			event.preventDefault(); // Prevent default browser behavior
			isSidebarCollapsed = !isSidebarCollapsed;
		}
	}

	async function addDatasetContext(dataset: { name: string; path: string }) {
		// Create new file for context
		const contextFileName = `${dataset.name} Context`;
		
		// Check if we already have this tab open
		const existingIndex = files.findIndex(f => f.name === contextFileName);
		if (existingIndex !== -1) {
			activeFileIndex = existingIndex;
			return;
		}

		// Fetch existing context if any
		try {
			const response = await fetchApi(`api/get-dataset-context/${dataset.name}`);
			const data = await response.json();
			
			const initialContent = data.exists ? data.content : `# ${dataset.name} Dataset Context\n\nAdd your dataset documentation here...\n`;
			
			// Create new file
			files = [...files, { 
				name: contextFileName, 
				content: initialContent,
				type: 'context' as const,
				datasetPath: dataset.path,
				datasetName: dataset.name // Add this to track which dataset this context belongs to
			}];
			activeFileIndex = files.length - 1;
			
			if (monaco && editor) {
				const model = monaco.editor.createModel(
					files[activeFileIndex].content,
					'markdown'
				);
				files[activeFileIndex].model = model;
				editor.setModel(files[activeFileIndex].model || null);
				editor.updateOptions({ theme: 'markdown-theme' });
			}
		} catch (error) {
			console.error('Error loading dataset context:', error);
			// Show error in console
			consoleEditor.setValue('🔴 Error: Failed to load dataset context');
		}
	}

	// Add a function to update editor theme based on file type
	function updateEditorTheme() {
		if (editor && files[activeFileIndex]) {
			const theme = files[activeFileIndex].type === 'context' ? 'markdown-theme' : 'my-theme';
			editor.updateOptions({ theme });
		}
	}

	async function saveDatasetContext() {
		const currentFile = files[activeFileIndex];
		if (currentFile.type !== 'context' || !editor) return;

		const content = editor.getValue();
		const datasetName = currentFile.datasetName;

		try {
			const response = await fetchApi('api/save-dataset-context', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					dataset_name: datasetName,
					content: content
				})
			});

			const result = await response.json();
			
			if (result.success) {
				consoleEditor.setValue('✅ Context saved successfully');
			} else {
				throw new Error(result.message || 'Failed to save context');
			}
		} catch (error) {
			console.error('Error saving context:', error);
			consoleEditor.setValue('🔴 Error: Failed to save context');
		}
	}

	async function restoreLastClosedTab() {
		const lastTab = closedTabs.restoreLastTab();
		if (!lastTab) return; // No tabs to restore

		// Create new file object
		const newFile: EditorFile = {
			name: lastTab.name,
			content: lastTab.content,
			type: lastTab.type as 'code' | 'dataset' | 'context' | 'home' | 'docs',
			datasetPath: lastTab.datasetPath || '',  // Ensure it's always a string
			datasetName: lastTab.datasetName
		};

		// Add the file
		files = [...files, newFile];
		activeFileIndex = files.length - 1;

		// Set up model for code or context files
		if ((lastTab.type === 'code' || lastTab.type === 'context') && monaco && editor) {
			const model = monaco.editor.createModel(
				lastTab.content,
				lastTab.type === 'context' ? 'markdown' : 'python'
			);
			files[activeFileIndex].model = model;
			editor.setModel(model);
			updateEditorTheme();
		}
	}

	// Add function to create or open Home tab
	function openHomeTab() {
		// Check if Home tab already exists
		const homeTabIndex = files.findIndex(file => file.type === 'home');
		
		if (homeTabIndex !== -1) {
			// If Home tab exists, switch to it
			activeFileIndex = homeTabIndex;
		} else {
			// If Home tab doesn't exist, create it
			const homeTab: EditorFile = {
				name: 'Home',
				content: '',
				type: 'home' as const,
				datasetPath: ''
			};
			
			// Add the Home tab as the first tab
			files = [homeTab, ...files];
			activeFileIndex = 0;
			
			// Save state after adding new file
			saveEditorState();
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		// Command/Ctrl + Shift + H (Home)
		if ((event.metaKey || event.ctrlKey) && event.shiftKey && (event.key === 'h' || event.key === 'H')) {
			event.preventDefault();
			event.stopPropagation();
			openHomeTab();
			return false;
		}
		
		// Command/Ctrl + Shift + P (Polars)
		if ((event.metaKey || event.ctrlKey) && event.shiftKey && (event.key === 'p' || event.key === 'P')) {
			event.preventDefault();
			event.stopPropagation();
			addNewTabWithContent('new_polars.py', codeTemplates.polars);
			return false;
		}

		// Command/Ctrl + Shift + L (SQL)
		if ((event.metaKey || event.ctrlKey) && event.shiftKey && (event.key === 'l' || event.key === 'L')) {
			event.preventDefault();
			event.stopPropagation();
			addNewTabWithContent('new_sql.py', codeTemplates.sql);
			return false;
		}

		// Command/Ctrl + Shift + B (Bokeh)
		if ((event.metaKey || event.ctrlKey) && event.shiftKey && (event.key === 'b' || event.key === 'B')) {
			event.preventDefault();
			event.stopPropagation();
			addNewTabWithContent('new_bokeh.py', codeTemplates.bokeh);
			return false;
		}

		// Command/Ctrl + Shift + E (Export File)
		if ((event.metaKey || event.ctrlKey) && event.shiftKey && (event.key === 'e' || event.key === 'E')) {
			event.preventDefault();
			event.stopPropagation();
			exportCurrentFile();
			return false;
		}

		// Existing Command/Ctrl + Shift + R handler
		if ((event.metaKey || event.ctrlKey) && event.shiftKey && event.key.toLowerCase() === 'r') {
			event.preventDefault();
			restoreLastClosedTab();
		}

		// Add new shortcut for Save Function (Cmd/Ctrl + Shift + F)
		if ((event.metaKey || event.ctrlKey) && event.shiftKey && (event.key === 'f' || event.key === 'F')) {
			event.preventDefault();
			event.stopPropagation();
			
			// Get selected code or current function
			let selectedCode = '';
			if (editor && files[activeFileIndex].type === 'code') {
				const selection = editor.getSelection();
				if (selection && !selection.isEmpty()) {
					selectedCode = editor.getModel()?.getValueInRange(selection) || '';
				} else {
					// If no selection, try to get the current function
					selectedCode = editor.getValue();
				}
			}
			
			showSaveFunctionModal = true;
			return false;
		}

		// Add new shortcut for Data Import (Cmd/Ctrl + Shift + I)
		if ((event.metaKey || event.ctrlKey) && event.shiftKey && (event.key === 'i' || event.key === 'I')) {
			event.preventDefault();
			event.stopPropagation();
			showDataImportModal = true;
			return false;
		}
	}

	// Add new helper function to create tabs with specific content
	function addNewTabWithContent(filename: string, content: string) {
		// Create new file object
		const newFile: EditorFile = {
			name: filename,
			content: content === '@sql\n' ? 
				'@sql\n\n--save_as:\n\n' : 
				content,
			type: 'code' as const,
			datasetPath: ''  // Ensure this is always a string
		};

		// Add the file
		files = [...files, newFile];
		activeFileIndex = files.length - 1;

		// Set up model for the new file if editor is available
		if (monaco && editor) {
			const model = monaco.editor.createModel(
				newFile.content,  // Use newFile.content instead of content
				'python'
			);
			files[activeFileIndex].model = model;
			editor.setModel(model);
			
			// Focus the editor
			editor.focus();
			
			// Place cursor at end of content
			editor.setPosition({ 
				lineNumber: model.getLineCount(), 
				column: model.getLineMaxColumn(model.getLineCount()) 
			});
		}

		// Save state after adding new file
		saveEditorState();
	}

	async function exportCurrentFile() {
		// Only allow exporting code files
		if (!editor || files[activeFileIndex]?.type !== 'code') {
			consoleEditor.setValue('⚠️ Only code files can be exported');
			return;
		}

		// Get the current file content and name
		const content = editor.getValue();
		let fileName = files[activeFileIndex].name;

		try {
			// Use the File System Access API if available (modern browsers)
			if ('showSaveFilePicker' in window) {
				const opts = {
					suggestedName: fileName,
					types: [{
						description: 'Python Files',
						accept: { 'text/plain': ['.py'] }
					}]
				};

				try {
					// @ts-ignore - TypeScript may not recognize this API yet
					const fileHandle = await window.showSaveFilePicker(opts);
					const writable = await fileHandle.createWritable();
					await writable.write(content);
					await writable.close();
					consoleEditor.setValue(`✅ File exported successfully to ${fileName}`);
				} catch (err: any) {
					// User probably cancelled the save dialog
					if (err.name !== 'AbortError') {
						throw err;
					}
				}
			} else {
				// Fallback to traditional download for browsers without File System Access API
				const blob = new Blob([content], { type: 'text/plain' });
				const url = URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = fileName;
				a.click();
				URL.revokeObjectURL(url);
				consoleEditor.setValue(`✅ File exported as ${fileName}`);
			}
		} catch (error: any) {
			console.error('Error exporting file:', error);
			consoleEditor.setValue(`🔴 Error exporting file: ${error.message}`);
		}
	}

	// Function to open the docs tab
	function openDocsTab() {
		// Check if Docs tab already exists
		const docsTabIndex = files.findIndex(file => file.type === 'docs');
		
		if (docsTabIndex !== -1) {
			// If Docs tab exists, switch to it
			activeFileIndex = docsTabIndex;
		} else {
			// If Docs tab doesn't exist, create it
			const docsTab: EditorFile = {
				name: 'Documentation',
				content: '',
				type: 'docs' as const,
				datasetPath: ''
			};
			
			// Add the Docs tab after Home tab or as first tab if no Home
			const homeTabIndex = files.findIndex(file => file.type === 'home');
			if (homeTabIndex !== -1) {
				files = [
					...files.slice(0, homeTabIndex + 1),
					docsTab,
					...files.slice(homeTabIndex + 1)
				];
				activeFileIndex = homeTabIndex + 1;
			} else {
				files = [docsTab, ...files];
				activeFileIndex = 0;
			}
			
			// Save state after adding new file
			saveEditorState();
		}
	}

	onMount(async () => {
		monaco = (await import('./monaco')).default;

		// Add markdown configuration
		monaco.languages.register({ id: 'markdown' });
		monaco.languages.setMonarchTokensProvider('markdown', {
			tokenizer: {
				root: [
					[/^##+\s.*/, 'heading'],
					[/\*\*([^*]|\*[^*])*\*\*/, 'strong'],
					[/\_\_([^_]|\_[^_])*\_\_/, 'strong'],
					[/\*([^*]|\*[^*])*\*/, 'emphasis'],
					[/\_([^_]|\_[^_])*\_/, 'emphasis'],
					[/\`[^`]*\`/, 'inline-code'],
					[/\`\`\`[\s\S]*?\`\`\`/, 'code-block'],
					[/\[([^\]]+)\]\(([^\)]+)\)/, 'link'],
					[/\!\[([^\]]+)\]\(([^\)]+)\)/, 'image'],
					[/\>.*$/, 'quote'],
					[/\-\s.*$/, 'list'],
					[/\*\s.*$/, 'list'],
					[/\d+\.\s.*$/, 'list'],
				]
			}
		});

		// Configure markdown theme
		monaco.editor.defineTheme('markdown-theme', {
			base: 'vs-dark',
			inherit: true,
			rules: [
				{ token: 'heading', foreground: '569CD6', fontStyle: 'bold' },
				{ token: 'strong', foreground: 'CE9178', fontStyle: 'bold' },
				{ token: 'emphasis', foreground: 'CE9178', fontStyle: 'italic' },
				{ token: 'inline-code', foreground: '6A9955' },
				{ token: 'code-block', foreground: '6A9955' },
				{ token: 'link', foreground: '569CD6' },
				{ token: 'image', foreground: '569CD6' },
				{ token: 'quote', foreground: '608B4E' },
				{ token: 'list', foreground: 'D4D4D4' }
			],
			colors: {
				'editor.background': '#1a1a1a',
				'editor.foreground': '#D4D4D4'
			}
		});

		monaco.editor.defineTheme('my-theme', {
			base: 'vs-dark',
			inherit: true,
			rules: [
				{ token: 'comment', foreground: '6A9955' },
				{ token: 'string', foreground: 'CE9178' },
				{ token: 'keyword', foreground: '569CD6' },
				{ token: 'number', foreground: 'B5CEA8' },
				{ token: 'operator', foreground: 'D4D4D4' },
				{ token: 'variable', foreground: '9CDCFE' },
				{ token: 'variable.predefined', foreground: '4FC1FF' },
				{ token: 'function', foreground: 'DCDCAA' },
				{ token: 'class', foreground: '4EC9B0' },
				{ token: 'type', foreground: '4EC9B0' },
			],
			colors: {
				'editor.background': '#1a1a1a',
				'editor.foreground': '#D4D4D4',
				'editor.lineHighlightBackground': '#2F323B',
				'editor.selectionBackground': '#264F78',
				'editor.inactiveSelectionBackground': '#3A3D41',
				'editorLineNumber.foreground': '#858585',
				'editorLineNumber.activeForeground': '#C6C6C6',
				'scrollbar.shadow': '#1a1a1a',
				'editorOverviewRuler.border': '#1a1a1a',
				'scrollbarSlider.background': '#333333',
				'scrollbarSlider.hoverBackground': '#404040'
			}
		});

		editor = monaco.editor.create(editorContainer, {
			automaticLayout: true,
			theme: 'my-theme',
			minimap: {
				enabled: false
			},
			fontSize: 12,
			lineHeight: 20,
			padding: {
				top: 16
			},
			suggestOnTriggerCharacters: false,
			quickSuggestions: false,
			snippetSuggestions: 'none',
			wordBasedSuggestions: 'off',
			parameterHints: {
				enabled: false
			},
			overviewRulerBorder: false,
			scrollbar: {
				useShadows: false
			}
		});
		
		// Add keyboard shortcut
		editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
			executeCode();
		});
		
		// Track changes and save state
		editor.onDidChangeModelContent(() => {
			setHasUnsavedChanges(true);
			saveEditorState();
		});

		// Restore editor state before creating initial model
		restoreEditorState();
		
		// Ensure Home tab exists after restoring state
		if (!files.some(file => file.type === 'home')) {
			files = [
				{
					name: 'Home',
					content: '',
					type: 'home' as const,
					datasetPath: ''
				},
				...files
			];
			// Adjust active file index if needed
			activeFileIndex++;
		}
		
		// Only create initial model if no saved state was restored
		if (!files[activeFileIndex]?.model) {
			// If active file is not Home and is a code or context file
			if (files[activeFileIndex].type !== 'home' && 
				(files[activeFileIndex].type === 'code' || files[activeFileIndex].type === 'context')) {
				const model = monaco.editor.createModel(
					files[activeFileIndex].content,
					files[activeFileIndex].type === 'context' ? 'markdown' : 'python'
				);
				files[activeFileIndex].model = model;
				editor.setModel(files[activeFileIndex].model || null);
			} else if (files[activeFileIndex].type === 'home') {
				// If active file is Home, clear the editor model
				editor.setModel(null);
			}
		}

		consoleEditor = monaco.editor.create(consoleContainer, {
			automaticLayout: true,
			theme: 'my-theme',
			minimap: {
				enabled: false
			},
			fontSize: 12,
			lineHeight: 20,
			readOnly: true,
			padding: {
				top: 16
			},
			renderLineHighlight: 'none',
			scrollBeyondLastLine: false,
			wordWrap: 'on',
			lineNumbers: 'off',
			glyphMargin: false,
			folding: false,
			guides: { indentation: false },
			overviewRulerBorder: false,
			overviewRulerLanes: 0,
			hideCursorInOverviewRuler: true
		});
		
		consoleEditor.setValue('// Console output will appear here');
		
		monaco.languages.registerHoverProvider('python', {
			async provideHover(model: Monaco.editor.ITextModel, position: Monaco.Position, token: Monaco.CancellationToken): Promise<Monaco.languages.Hover | null> {
				// Check if this is actually Python code
				if (model.getLanguageId() !== 'python') return null;

				try {
					const code = model.getValue();
					const response = await fetchApi('lint', {
						method: 'POST',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify({ 
							code,
							line: position.lineNumber,
							column: position.column
						})
					});

					const lintResults = await response.json();
					
					if (lintResults.length === 0) {
						return null;
					}
					
					// Format the hover message
					const contents = lintResults.map((error: any) => ({
						value: `${error.message} (${error.code})`
					}));

					return {
						contents,
						range: {
							startLineNumber: position.lineNumber,
							startColumn: position.column,
							endLineNumber: position.lineNumber,
							endColumn: position.column + 1
						}
					};
				} catch (error) {
					console.error('Linting failed:', error);
					return null;
				}
			}
		});

		loadDatasets();
		
		// Add click outside listener for dropdowns
		document.addEventListener('click', handleClickOutside);

		// Add global keyboard shortcut listener
		window.addEventListener('keydown', handleKeyboardShortcut);

		// Add event listener for opening docs tab
		window.addEventListener('openDocs', openDocsTab);

		// Add keyboard shortcut to Monaco editor
		editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyD, () => {
			isSidebarCollapsed = !isSidebarCollapsed;
		});

		// Add save shortcut for context files
		editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
			if (files[activeFileIndex]?.type === 'context') {
				saveDatasetContext();
			}
		});
	});

	onDestroy(() => {
		// Save state before destroying
		saveEditorState();
		monaco?.editor.getModels().forEach((model: any) => model.dispose());
		editor?.dispose();
		consoleEditor?.dispose();
		document.removeEventListener('click', handleClickOutside);

		// Remove global keyboard shortcut listener
		window.removeEventListener('keydown', handleKeyboardShortcut);
		
		// Remove docs tab event listener
		window.removeEventListener('openDocs', openDocsTab);
	});

	function startResize(e: MouseEvent) {
		resizing = true;
		document.body.classList.add('resizing');
		window.addEventListener('mousemove', handleResize);
		window.addEventListener('mouseup', stopResize);
	}

	function handleResize(e: MouseEvent) {
		if (!resizing) return;
		
		const container = document.querySelector('.editors-container');
		if (!container) return;
		
		const containerRect = container.getBoundingClientRect();
		const mouseY = Math.min(Math.max(e.clientY, containerRect.top), containerRect.bottom);
		const percentage = ((mouseY - containerRect.top) / containerRect.height) * 100;
		
		// Clamp the percentage between 20% and 80%
		const clampedPercentage = Math.min(Math.max(percentage, 20), 80);
		editorHeight = `${clampedPercentage}%`;
		
		// Force Monaco editors to update their layout
		requestAnimationFrame(() => {
			editor?.layout();
			consoleEditor?.layout();
		});
	}

	function stopResize() {
		resizing = false;
		document.body.classList.remove('resizing');
		window.removeEventListener('mousemove', handleResize);
		window.removeEventListener('mouseup', stopResize);
	}

	function startRename(index: number, event: MouseEvent) {
		if (event.detail === 2) {
			event.preventDefault();
			editingFileName = index;
		}
	}

	function handleRename(index: number, event: KeyboardEvent) {
		const input = event.target as HTMLInputElement;
		
		if (event.key === 'Enter') {
			const newName = input.value.trim();
			// Only allow renaming if it's not a dataset tab
			if (newName && newName !== files[index].name && files[index].type !== 'dataset') {
				const oldName = files[index].name;
				files[index].name = newName;
				files = [...files];
				
				// If this is a code tab, also rename the version folder
				if (files[index].type === 'code') {
					renameVersionFolder(oldName, newName).catch(error => {
						console.error('Failed to rename version folder:', error);
						// Silent fail - don't disrupt workflow
					});
				}
			}
			editingFileName = -1;
		} else if (event.key === 'Escape') {
			editingFileName = -1;
		}
	}

	// Function to rename version folder
	async function renameVersionFolder(oldName: string, newName: string) {
		try {
			const response = await fetchApi('api/rename-version-folder', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					old_name: oldName,
					new_name: newName
				})
			});
			
			const result = await response.json();
			console.log('Version folder rename result:', result);
			
		} catch (error) {
			console.error('Error renaming version folder:', error);
			// Silent fail - don't disrupt workflow
		}
	}

	function handleRenameBlur() {
		editingFileName = -1;
	}

	function handleDataImportClose() {
		showDataImportModal = false;
		loadDatasets(); // Refresh dataset list after import
	}

	// Add this function after handleRenameBlur()
	function handleLoadVersion(event: CustomEvent) {
		const { code, version } = event.detail;
		
		// Only handle if a code tab is active
		if (files[activeFileIndex]?.type === 'code') {
			// Update the editor with the loaded version
			editor.setValue(code);
			
			// Show a notification in the console
			consoleEditor.setValue(`✅ Loaded version from ${version.timestamp}`);
		}
	}
</script>

<svelte:head>
	<title>Mako Code</title>
</svelte:head>

<div class="flex-1 flex flex-col overflow-hidden">
	<div class="flex h-screen bg-[#1a1a1a]">
		<div class="w-[60%] flex flex-col flex-1" style="width: {isSidebarCollapsed ? '97%' : '60%'}; transition: all 0.05s ease-in-out;">
			<div class="flex flex-col">
				<div class="flex items-center space-x-0 pt-2.5 overflow-x-auto">
					{#each files as file, index}
						<button
							class="tab-button px-3 py-1.5 {index === 0 ? 'border-l' : ''} border-t border-r border-[#333333] 
								   bg-[#1a1a1a] text-gray-400 hover:bg-[#252525]
								   {index === activeFileIndex ? 'border-t-2 border-t-white -mt-[1px] text-white' : ''}
								   {draggedTabIndex === index ? 'opacity-50' : ''}
								   flex items-center min-w-[100px] max-w-[200px] group font-mono text-xs"
							on:click={() => switchFile(index)}
							on:mousedown={(e) => startRename(index, e)}
							draggable="true"
							on:dragstart={(e) => handleDragStart(index, e)}
							on:dragover={(e) => handleDragOver(index, e)}
							on:dragend={handleDragEnd}
						>
							{#if editingFileName === index}
								<input
									type="text"
									value={file.name}
									class="bg-transparent border-none outline-none text-white w-full"
									on:keydown={(e) => handleRename(index, e)}
									on:blur={handleRenameBlur}
									autofocus
								/>
							{:else}
								<span class="truncate flex-1">{file.name}</span>
							{/if}
							<span
								class="opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity px-1 text-lg"
								on:click|stopPropagation={() => removeFile(index)}
							>
								×
							</span>
						</button>
					{/each}
					<button
						on:click={addNewFile}
						class="px-3 py-1.5 bg-[#1a1a1a] text-gray-400 hover:bg-[#252525]"
					>
						+
					</button>
					
					<div class="flex-1"></div>
					
					<span class="text-gray-400 text-xs pr-2.5 font-mono">Press ⌘/Ctrl + Enter to run</span>
				</div>
			</div>
			
			<div class="editors-container flex-1 flex flex-col">
				<div 
					class="editor-wrapper"
					style="height: {editorHeight}"
				>
					<!-- Editor container always exists but conditionally visible -->
					<div 
						class="editor-container" 
						style:display={files[activeFileIndex].type === 'code' || files[activeFileIndex].type === 'context' ? 'block' : 'none'}
						bind:this={editorContainer}
					/>
					
					<!-- Home view -->
					{#if files[activeFileIndex].type === 'home'}
						<div class="home-container p-8 h-full overflow-auto bg-[#1a1a1a] text-gray-300 font-mono">
							<h1 class="text-2xl font-bold mb-6 text-white">What is Mako Code?</h1>
							
							<p class="mb-4">
								Mako Code is your own personal Polars sketchpad. It is an open source Independent Analytics Environment (IAE) that is built for data people who love to code. It is a workflow designed for fast ad hoc analysis with features to let you productize your work. So you can get to answers quickly while building a foundation for future data products.							</p>
							
							<p class="mb-6">
								Mako Code is not a vibe coding tool, and doesn't come with an LLM. But it does come with an opinion.
							</p>
							
							<ul class="list-disc pl-6 mb-8 space-y-1">
								<li>All built in python functions</li>
								<li>Polars for data processing</li>
								<li>Bokeh for plotting</li>
								<li>Pyarrow for data transfer</li>
							</ul>
							
							<h2 class="text-xl font-bold mb-4 text-white">Getting Started</h2>
							
							<p class="mb-4">
								First things first. You can try importing local data using the shortcut <span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + Shift + I</span>
							</p>

							<p class="mb-4">If you need a dataset to look at, try this Airbnb dataset from Kaggle: <a href="https://www.kaggle.com/datasets/dgomonov/new-york-city-airbnb-open-data" target="_blank" class="text-blue-400 hover:underline">New York City Airbnb Open Data</a></p>

							<p class="mb-4">
								Once you have data imported, you can analyze it in the right side data management bar. Here's how:
							</p>

							<ol class="list-decimal pl-6 mb-8 space-y-2">
								<li>Open the data management sidebar using <span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + D</span></li>
								<li>Find your dataset in the list</li>
								<li>Click on your dataset name to open a data view tab in the editor</li>
								<li>This will open a new tab with a detailed view of your data including:
									<ul class="list-disc pl-6 mt-2 space-y-1">
										<li>Column names and types</li>
										<!-- <li>Basic statistics</li> -->
										<li>Sample data preview</li>
										<li>A context window to add notes and documentation</li>
										<!-- <li>Memory usage information</li> -->
									</ul>
								</li>
								<li>Now click on the elipses menu next to the dataset in the right side menu and select "Analyze" </li>
								<li>This will open a new tab with pre created polars code allowing you start analyzing your data immediately</li>
							</ol>
							
							<h2 class="text-xl font-bold mt-8 mb-4 text-white">Interface Overview</h2>
							
							<p class="mb-2">Mako Code has a few sections:</p>
							<ul class="list-disc pl-6 mb-8 space-y-1">
								<li>Left Side menu shows the functions you create and also all shortcuts.</li>
								<li>The right side menu (open using <span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + D</span>) opens the data management folder.</li>
								<li>You can view your local datasets here and delete, analyze or add context.</li>
							</ul>
							
							<h2 class="text-xl font-bold mt-8 mb-4 text-white">Keyboard Shortcuts</h2>
							
							<div class="grid grid-cols-2 gap-4 mb-8">
								<div>
									<h3 class="text-lg font-bold mb-2 text-white">Code Execution</h3>
									<ul class="space-y-2">
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + Enter</span> - Run current file</li>
									</ul>
								</div>
								
								<div>
									<h3 class="text-lg font-bold mb-2 text-white">Tab Management</h3>
									<ul class="space-y-2">
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + Shift + P</span> - New Polars file</li>
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + Shift + L</span> - New SQL file</li>
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + Shift + B</span> - New Bokeh file</li>
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + Shift + R</span> - Restore last closed tab</li>
									</ul>
								</div>
								
								<div>
									<h3 class="text-lg font-bold mb-2 text-white">Navigation</h3>
									<ul class="space-y-2">
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + D</span> - Toggle Data Management sidebar</li>
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + Shift + H</span> - Open Home tab</li>
									</ul>
								</div>
								
								<div>
									<h3 class="text-lg font-bold mb-2 text-white">Data Management</h3>
									<ul class="space-y-2">
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + Shift + I</span> - Open Data Import</li>
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + Shift + F</span> - Save new function</li>
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + Shift + E</span> - Export current file</li>
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + S</span> - Save context file</li>
									</ul>
								</div>
							</div>
						</div>
					{/if}
					
					{#if files[activeFileIndex].type === 'docs'}
						<div class="docs-container p-8 h-full overflow-auto bg-[#1a1a1a] text-gray-300 font-mono">
							<h1 class="text-2xl font-bold mb-6 text-white">Mako Code Documentation</h1>
							
							<!-- Table of Contents -->
							<div class="mb-8 p-4 bg-[#222222] rounded-lg">
								<h2 class="text-lg font-bold mb-4 text-white">Table of Contents</h2>
								<ul class="space-y-2">
									<li><a href="#api-endpoints" class="text-blue-400 hover:underline">FastAPI Endpoints</a></li>
									<li><a href="#save-function" class="text-blue-400 hover:underline">Using the Save Function</a></li>
									<li><a href="#user-functions" class="text-blue-400 hover:underline">User-Defined Functions</a></li>
								</ul>
							</div>
							
							<!-- API Endpoints Section -->
							<section id="api-endpoints" class="mb-8">
								<h2 class="text-xl font-bold mb-4 text-white">FastAPI Endpoints</h2>
								<p class="mb-4">
									Mako Code provides several backend API endpoints for interacting with data, executing code, and managing your environment. 
									Below are the key endpoints and their functionalities:
								</p>
								
								<div class="space-y-6">
									<div class="p-4 bg-[#222222] rounded-lg">
										<h3 class="text-lg font-bold mb-2 text-white">/execute</h3>
										<p class="mb-2">Executes Python code submitted from the editor.</p>
										<ul class="list-disc pl-6 mb-2 space-y-1">
											<li><strong>Method:</strong> POST</li>
											<li><strong>Body:</strong> JSON with "code" field containing the Python code to execute</li>
											<li><strong>Returns:</strong> Execution output, stdout, stderr, and execution success status</li>
										</ul>
									</div>
									
									<div class="p-4 bg-[#222222] rounded-lg">
										<h3 class="text-lg font-bold mb-2 text-white">/api/list-datasets</h3>
										<p class="mb-2">Retrieves a list of available datasets in the local storage.</p>
										<ul class="list-disc pl-6 mb-2 space-y-1">
											<li><strong>Method:</strong> GET</li>
											<li><strong>Returns:</strong> JSON list of dataset names and paths</li>
										</ul>
									</div>
									
									<div class="p-4 bg-[#222222] rounded-lg">
										<h3 class="text-lg font-bold mb-2 text-white">/api/delete-dataset</h3>
										<p class="mb-2">Deletes a dataset from local storage.</p>
										<ul class="list-disc pl-6 mb-2 space-y-1">
											<li><strong>Method:</strong> POST</li>
											<li><strong>Body:</strong> JSON with "path" field for the dataset to delete</li>
											<li><strong>Returns:</strong> Success status</li>
										</ul>
									</div>
									
									<div class="p-4 bg-[#222222] rounded-lg">
										<h3 class="text-lg font-bold mb-2 text-white">/api/dataset/&#123;dataset_path&#125;</h3>
										<p class="mb-2">Retrieves dataset content for viewing and analysis.</p>
										<ul class="list-disc pl-6 mb-2 space-y-1">
											<li><strong>Method:</strong> GET</li>
											<li><strong>Path Parameter:</strong> dataset_path - Path to the dataset</li>
											<li><strong>Returns:</strong> JSON with dataset schema, preview rows, and statistics</li>
										</ul>
									</div>
									
									<div class="p-4 bg-[#222222] rounded-lg">
										<h3 class="text-lg font-bold mb-2 text-white">/lint</h3>
										<p class="mb-2">Performs code linting using Ruff to check for errors and style issues.</p>
										<ul class="list-disc pl-6 mb-2 space-y-1">
											<li><strong>Method:</strong> POST</li>
											<li><strong>Body:</strong> JSON with code and cursor position</li>
											<li><strong>Returns:</strong> List of lint errors and warnings</li>
										</ul>
									</div>
									
									<div class="p-4 bg-[#222222] rounded-lg">
										<h3 class="text-lg font-bold mb-2 text-white">/api/save-dataset-context</h3>
										<p class="mb-2">Saves documentation context for a dataset.</p>
										<ul class="list-disc pl-6 mb-2 space-y-1">
											<li><strong>Method:</strong> POST</li>
											<li><strong>Body:</strong> JSON with dataset_name and content</li>
											<li><strong>Returns:</strong> Success status</li>
										</ul>
									</div>
									
									<div class="p-4 bg-[#222222] rounded-lg">
										<h3 class="text-lg font-bold mb-2 text-white">/api/save-function</h3>
										<p class="mb-2">Saves a user-defined function for reuse.</p>
										<ul class="list-disc pl-6 mb-2 space-y-1">
											<li><strong>Method:</strong> POST</li>
											<li><strong>Body:</strong> JSON with function code and metadata</li>
											<li><strong>Returns:</strong> Success status and function ID</li>
										</ul>
									</div>
								</div>
							</section>
							
							<!-- Save Function Section -->
							<section id="save-function" class="mb-8">
								<h2 class="text-xl font-bold mb-4 text-white">Using the Save Function</h2>
								<p class="mb-4">
									The <code class="bg-[#333] px-2 py-0.5 rounded">save()</code> function in <code class="bg-[#333] px-2 py-0.5 rounded">functions.mako</code> allows you to persistently store 
									Polars DataFrames or LazyFrames as parquet files in the local storage directory.
								</p>
								
								<div class="p-4 bg-[#222222] rounded-lg mb-4">
									<h3 class="text-lg font-bold mb-2 text-white">Function Signature</h3>
									<p class="mb-2">
										<code class="bg-[#333] px-2 py-0.5 rounded">save(df: Union[pl.DataFrame, pl.LazyFrame], filename: str) -> Union[pl.DataFrame, pl.LazyFrame]</code>
									</p>
									
									<h4 class="text-md font-bold mt-4 mb-2 text-white">Parameters</h4>
									<ul class="list-disc pl-6 mb-2 space-y-1">
										<li><strong>df:</strong> The DataFrame or LazyFrame to save</li>
										<li><strong>filename:</strong> Name for the saved file (without extension)</li>
									</ul>
									
									<h4 class="text-md font-bold mt-4 mb-2 text-white">Returns</h4>
									<p class="mb-2">The original DataFrame or LazyFrame for method chaining</p>
								</div>
								
								<div class="p-4 bg-[#222222] rounded-lg">
									<h3 class="text-lg font-bold mb-2 text-white">Key Features</h3>
									<ul class="list-disc pl-6 mb-4 space-y-1">
										<li>Automatically handles both DataFrames and LazyFrames</li>
										<li>Creates necessary directories if they don't exist</li>
										<li>Saves files in the parquet format for efficient storage</li>
										<li>Supports method chaining by returning the original dataframe</li>
										<li>Displays informative messages about the save operation</li>
									</ul>
									
									<h3 class="text-lg font-bold mb-2 mt-4 text-white">Common Usage Patterns</h3>
									<p class="mb-2">
										The save function is typically used at the end of a data processing pipeline to preserve the results:
									</p>
									<ul class="list-disc pl-6 space-y-1">
										<li>Save after filtering, aggregating, or transforming data</li>
										<li>Save intermediate results in multi-step workflows</li>
										<li>Save results of SQL queries by using it with SQL decorator output</li>
									</ul>
								</div>
							</section>
							
							<!-- User-Defined Functions Section -->
							<section id="user-functions" class="mb-8">
								<h2 class="text-xl font-bold mb-4 text-white">User-Defined Functions</h2>
								<p class="mb-4">
									Mako Code allows you to save your own custom functions for reuse across different analysis sessions.
									This feature helps you build a personal library of utility functions tailored to your specific needs.
								</p>
								
								<div class="p-4 bg-[#222222] rounded-lg mb-4">
									<h3 class="text-lg font-bold mb-2 text-white">Creating User Functions</h3>
									<ol class="list-decimal pl-6 mb-4 space-y-1">
										<li>Write your function in a code tab with proper Python function definition</li>
										<li>Select the function code (or the entire file if it contains only one function)</li>
										<li>Press <span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + Shift + F</span> to open the Save Function dialog</li>
										<li>Enter a name, description, and optional categories for your function</li>
										<li>Click "Save Function" to store it in your personal library</li>
									</ol>
									
									<h4 class="text-md font-bold mt-4 mb-2 text-white">Function Metadata</h4>
									<ul class="list-disc pl-6 mb-2 space-y-1">
										<li><strong>Name:</strong> Unique identifier for your function</li>
										<li><strong>Description:</strong> Brief explanation of what the function does</li>
										<li><strong>Categories:</strong> Tags to organize and filter functions</li>
									</ul>
								</div>
								
								<div class="p-4 bg-[#222222] rounded-lg">
									<h3 class="text-lg font-bold mb-2 text-white">Using Saved Functions</h3>
									<ol class="list-decimal pl-6 mb-4 space-y-1">
										<li>Click on the "Functions" button in the left sidebar to open the Functions modal</li>
										<li>Browse or search for your saved function</li>
										<li>Click on a function to view its details</li>
										<li>Use the "Insert" button to add the function to your current code</li>
										<li>Alternatively, click "New Tab" to create a new file with the function</li>
									</ol>
									
									<h3 class="text-lg font-bold mb-2 mt-4 text-white">Function Management</h3>
									<ul class="list-disc pl-6 space-y-1">
										<li>Functions are stored persistently and available across sessions</li>
										<li>You can delete functions you no longer need</li>
										<li>Functions can be updated by saving with the same name</li>
										<li>Functions can be exported and shared with other Mako Code users</li>
									</ul>
								</div>
							</section>
						</div>
					{/if}
					
					<!-- Dataset view only renders when needed -->
					{#if files[activeFileIndex].type === 'dataset' && files[activeFileIndex].datasetPath}
						<EnhancedDatasetView 
							datasetPath={files[activeFileIndex].datasetPath} 
							datasetName={files[activeFileIndex].name.replace('.parquet', '')}
						/>
					{:else if files[activeFileIndex].type === 'dataset'}
						<div class="flex items-center justify-center h-full text-red-400">
							Error: Dataset path not specified
						</div>
					{/if}
				</div>
				
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<!-- svelte-ignore element_invalid_self_closing_tag -->
				<div 
					class="resize-handle"
					style="background-color: #2A2A2A"
					on:mousedown={startResize}
				/>
				
				<div class="console-wrapper border-t border-[#333333]">
					<!-- svelte-ignore element_invalid_self_closing_tag -->
					<div class="console-container" bind:this={consoleContainer} />
				</div>
			</div>
		</div>
		
		<RightSidebar 
			bind:isSidebarCollapsed
			{datasets}
			{addDatasetTab}
			{deleteDataset}
			{addDatasetContext}
			{analyzeDataset}
			activeFile={files[activeFileIndex] ? { name: files[activeFileIndex].name, type: files[activeFileIndex].type } : { name: '', type: '' }}
			on:importClick={() => showDataImportModal = true}
			on:loadVersion={handleLoadVersion}
		/>
	</div>
</div>

<DataImportModal
	show={showDataImportModal}
	onClose={handleDataImportClose}
/>

<SaveFunctionModal
	show={showSaveFunctionModal}
	onClose={() => showSaveFunctionModal = false}
	initialCode={editor?.getSelection()?.isEmpty() ? '' : editor?.getModel()?.getValueInRange(editor.getSelection()!) || ''}
/>

<svelte:window 
	on:keydown|capture={handleKeydown}
/>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		background-color: #1a1a1a;
	}

	.editors-container {
		position: relative;
		min-height: 0; /* Important for flex container */
	}

	.editor-wrapper {
		transition: height 0.05s ease;
		min-height: 100px; /* Add minimum height */
		max-height: calc(100% - 100px); /* Ensure there's always space for console */
	}

	.console-wrapper {
		flex: 1; /* Take remaining space */
		min-height: 100px; /* Minimum height when resizing */
		border-top: 1px solid #333333;
	}

	.editor-container, .console-container {
		height: 100%;
		width: 100%;
		background-color: #1a1a1a;
	}

	.resize-handle {
		height: 6px;
		background-color: #2A2A2A;
		cursor: row-resize;
		transition: background-color 0.2s;
		user-select: none;
		touch-action: none;
		z-index: 10;
	}

	.resize-handle:hover {
		background-color: #404040;
	}

	:global(body.resizing) {
		user-select: none;
		cursor: row-resize !important;
	}

	.right-panel {
		scrollbar-width: thin;
		scrollbar-color: var(--bg-hover) var(--bg-primary);
	}

	.right-panel::-webkit-scrollbar {
		width: 8px;
	}

	.right-panel::-webkit-scrollbar-track {
		background: var(--bg-primary);
	}

	.right-panel::-webkit-scrollbar-thumb {
		background-color: var(--bg-hover);
		border-radius: 4px;
	}

	/* Add new styles for the tabs */
	button {
		outline: none;
		transition: all 0.2s;
	}

	.overflow-x-auto {
		scrollbar-width: thin;
		scrollbar-color: var(--bg-hover) var(--bg-primary);
	}

	.overflow-x-auto::-webkit-scrollbar {
		height: 8px;
	}

	.overflow-x-auto::-webkit-scrollbar-track {
		background: var(--bg-primary);
	}

	.overflow-x-auto::-webkit-scrollbar-thumb {
		background-color: var(--bg-hover);
		border-radius: 4px;
	}
	
	/* Home tab styles */
	.home-container {
		font-family: 'Courier New', monospace;
		line-height: 1.6;
		font-size: 0.9rem;
	}
	
	.home-container h1 {
		font-family: 'Courier New', monospace;
		font-weight: bold;
		font-size: 1.5rem;
	}
	
	.home-container h2 {
		font-family: 'Courier New', monospace;
		font-weight: bold;
		font-size: 1.2rem;
	}
	
	.home-container h3 {
		font-family: 'Courier New', monospace;
		font-weight: bold;
		font-size: 1rem;
	}
	
	.home-container ul {
		margin-left: 1.5rem;
	}
	
	.home-container p {
		margin-bottom: 1rem;
	}
	
	.home-container .bg-\[\#333\] {
		display: inline-block;
		margin: 0 0.25rem;
		font-size: 0.8rem;
	}
	
	/* Docs tab styles */
	.docs-container {
		font-family: 'Courier New', monospace;
		line-height: 1.6;
		font-size: 0.9rem;
	}
	
	.docs-container h1 {
		font-family: 'Courier New', monospace;
		font-weight: bold;
		font-size: 1.5rem;
	}
	
	.docs-container h2 {
		font-family: 'Courier New', monospace;
		font-weight: bold;
		font-size: 1.2rem;
		scroll-margin-top: 2rem;
	}
	
	.docs-container h3 {
		font-family: 'Courier New', monospace;
		font-weight: bold;
		font-size: 1rem;
	}
	
	.docs-container ul,
	.docs-container ol {
		margin-left: 1.5rem;
	}
	
	.docs-container p {
		margin-bottom: 1rem;
	}
	
	.docs-container .bg-\[\#333\] {
		display: inline-block;
		margin: 0 0.25rem;
		font-size: 0.8rem;
	}
	
	.docs-container section {
		padding-top: 1rem;
		border-top: 1px solid #333333;
	}
	
	.docs-container code {
		font-family: 'Courier New', monospace;
	}
</style>