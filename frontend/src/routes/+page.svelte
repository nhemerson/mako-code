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
	import { getApiUrl, fetchApi } from "$lib/utils/api";
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { writable } from 'svelte/store';

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

	const languages = [
		{ id: 'python' as const, name: 'Python' },
		{ id: 'sql' as const, name: 'SQL' },
		{ id: 'rust' as const, name: 'Rust' },
		{ id: 'javascript' as const, name: 'JavaScript' }
	];

	interface EditorFile {
		name: string;
		content: string;
		model?: Monaco.editor.ITextModel;
		type: 'code' | 'dataset' | 'context' | 'home';
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
		} catch (error: any) {
			console.error('Code execution error:', error);
			const errorMessage = '\x1b[31m🔴 Error: Failed to execute code. Make sure the backend server is running.\n' + error.message + '\x1b[0m';
			consoleEditor.setValue(errorMessage);
			consoleEditor.revealLine(consoleEditor.getModel()?.getLineCount() || 1);
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
			type: lastTab.type as 'code' | 'dataset' | 'context' | 'home',
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
			if (newName && newName !== files[index].name) {
				files[index].name = newName;
				files = [...files];
			}
			editingFileName = -1;
		} else if (event.key === 'Escape') {
			editingFileName = -1;
		}
	}

	function handleRenameBlur() {
		editingFileName = -1;
	}

	function handleDataImportClose() {
		showDataImportModal = false;
		loadDatasets(); // Refresh dataset list after import
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
							<h1 class="text-2xl font-bold mb-6 text-white">What is Mako?</h1>
							
							<p class="mb-4">
								Mako is a modern web-based analytics platform that combines the power of an interactive code editor with robust data management capabilities. It provides data scientists, analysts, and developers with a seamless environment for writing, executing, and analyzing python code alongside powerful data visualization features.
							</p>
							
							<p class="mb-6">
								Mako is an analytics IDE with an opinion. Out of the box, it allows for a small set of python modules to be imported and used.
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
							
							<h2 class="text-xl font-bold mt-8 mb-4 text-white">Interface Overview</h2>
							
							<p class="mb-2">Mako has a few sections:</p>
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
										<li><span class="bg-[#333] px-2 py-1 rounded">⌘/Ctrl + S</span> - Save context file</li>
									</ul>
								</div>
							</div>
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
			on:importClick={() => showDataImportModal = true}
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
</style>