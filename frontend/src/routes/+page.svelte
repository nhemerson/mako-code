<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';
	import { setHasUnsavedChanges } from '$lib/stores/navigation';
	import DataImportModal from '$lib/components/DataImportModal.svelte';
	import DataframeView from '$lib/components/DataframeView.svelte';
	import EnhancedDatasetView from '$lib/components/EnhancedDatasetView.svelte';
	import { closedTabs } from '$lib/stores/editorStore';

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

	const languages = [
		{ id: 'python' as const, name: 'Python' },
		{ id: 'sql' as const, name: 'SQL' },
		{ id: 'rust' as const, name: 'Rust' },
		{ id: 'javascript' as const, name: 'JavaScript' }
	];

	const sampleCode: Record<'python' | 'sql' | 'rust' | 'javascript', string> = {
		python: `# Python example
def greet(name):
    return f"Hello, {name}!"

message = greet("World")
print(message)

# List comprehension example
numbers = [1, 2, 3, 4, 5]
squares = [n ** 2 for n in numbers]
print(f"Squares: {squares}")`,
		sql: `-- SQL example
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    age INTEGER
);

INSERT INTO users (name, age) VALUES
    ('Alice', 30),
    ('Bob', 25);

SELECT name, age
FROM users
WHERE age >= 25
ORDER BY name;`,
		rust: `// Rust example
fn main() {
    println!("Hello from Rust!");
    
    let numbers = vec![1, 2, 3, 4, 5];
    for n in numbers {
        println!("{}", n * 2);
    }
}`,
		javascript: `// JavaScript example
console.log('Hello from JavaScript!');

// Array operations
const numbers = [1, 2, 3, 4, 5];
const doubled = numbers.map(n => n * 2);
console.log('Doubled numbers:', doubled);`
	};

	interface EditorFile {
		name: string;
		content: string;
		model?: Monaco.editor.ITextModel;
		type: 'code' | 'dataset' | 'context';
		datasetPath: string;
		datasetName?: string;
	}

	let files: EditorFile[] = [
		{ 
			name: 'main.py', 
			content: '# Python example\nprint("Hello World!")', 
			type: 'code',
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
			datasetPath: file.datasetPath || ''
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
				files = parsedFiles.map((file: any) => ({
					...file,
					datasetPath: file.datasetPath || ''
				}));
				
				if (savedActiveIndex) {
					activeFileIndex = parseInt(savedActiveIndex, 10);
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
			type: 'code',
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
	}

	function changeLanguage() {
		const model = editor.getModel();
		if (model) {
			monaco.editor.setModelLanguage(model, selectedLanguage);
			editor.setValue(sampleCode[selectedLanguage]);
		}
	}

	async function executeCode() {
		const code = editor.getValue();
		consoleEditor.setValue('Running...\n');
		output = ''; // Reset output at start

		try {
			const response = await fetch('http://localhost:8000/execute', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ code })
			});

			const result = await response.json();
			
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
			const errorMessage = '\x1b[31m🔴 Error: Failed to execute code. Make sure the backend server is running.\n' + error.message + '\x1b[0m';
			consoleEditor.setValue(errorMessage);
			consoleEditor.revealLine(consoleEditor.getModel()?.getLineCount() || 1);
		}
	}

	function addDatasetTab(datasetName: string, datasetPath: string) {
		// Check if a tab for this dataset already exists
		const existingIndex = files.findIndex(f => 
			f.type === 'dataset' && 
			f.datasetPath === datasetPath
		);
		if (existingIndex !== -1) {
			// If it exists, switch to it
			activeFileIndex = existingIndex;
			return;
		}

		// Add new tab
		const newFile: EditorFile = { 
			name: datasetName,
			content: '',  // Dataset tabs don't need content
			type: 'dataset',
			datasetPath,
			datasetName
		};
		files = [...files, newFile];
		activeFileIndex = files.length - 1;
	}

	async function loadDatasets() {
		try {
			const response = await fetch('http://localhost:8000/api/list-datasets');
			const data = await response.json();
			datasets = data.datasets;
		} catch (error) {
			console.error('Failed to load datasets:', error);
		}
	}

	async function deleteDataset(datasetPath: string) {
		try {
			const response = await fetch('http://localhost:8000/api/delete-dataset', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ path: datasetPath })
			});

			if (response.ok) {
				// Remove the dataset from the list
				datasets = datasets.filter(d => d.path !== datasetPath);
				// Close any open tabs for this dataset
				files = files.filter(f => f.type !== 'dataset' || f.datasetPath !== datasetPath);
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
			type: 'code',
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
			const response = await fetch(`http://localhost:8000/api/get-dataset-context/${dataset.name}`);
			const data = await response.json();
			
			const initialContent = data.exists ? data.content : `# ${dataset.name} Dataset Context\n\nAdd your dataset documentation here...\n`;
			
			// Create new file
			files = [...files, { 
				name: contextFileName, 
				content: initialContent,
				type: 'context',
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
			const response = await fetch('http://localhost:8000/api/save-dataset-context', {
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

	function handleKeydown(event: KeyboardEvent) {
		// Command/Ctrl + Shift + P (Polars)
		if ((event.metaKey || event.ctrlKey) && event.shiftKey && (event.key === 'p' || event.key === 'P')) {
			event.preventDefault();
			event.stopPropagation();
			addNewTabWithContent('new_polars.py', '#https://docs.pola.rs/api/python/stable/reference/\n\nimport polars as pl\n\ndata = {"a": [1, 2], "b": [3, 4]}\ndf = pl.DataFrame(data)\ndf');
			return false;
		}

		// Command/Ctrl + Shift + L (SQL)
		if ((event.metaKey || event.ctrlKey) && event.shiftKey && (event.key === 'l' || event.key === 'L')) {
			event.preventDefault();
			event.stopPropagation();
			addNewTabWithContent('new_sql.py', '@sql\n');
			return false;
		}

		// Existing Command/Ctrl + Shift + R handler
		if ((event.metaKey || event.ctrlKey) && event.shiftKey && event.key.toLowerCase() === 'r') {
			event.preventDefault();
			restoreLastClosedTab();
		}
	}

	async function restoreLastClosedTab() {
		const lastTab = closedTabs.restoreLastTab();
		if (!lastTab) return; // No tabs to restore

		// Create new file object
		const newFile = {
			name: lastTab.name,
			content: lastTab.content,
			type: lastTab.type,
			datasetPath: lastTab.datasetPath,
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

	// Add new helper function to create tabs with specific content
	function addNewTabWithContent(filename: string, content: string) {
		// Create new file object
		const newFile: EditorFile = {
			name: filename,
			content: content === '@sql\n' ? 
				'@sql\n\n--save_as:\n\n' : 
				content,
			type: 'code',
			datasetPath: ''
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
		
		// Only create initial model if no saved state was restored
		if (!files[activeFileIndex]?.model) {
			const model = monaco.editor.createModel(
				files[activeFileIndex].content,
				'python'
			);
			files[activeFileIndex].model = model;
			editor.setModel(files[activeFileIndex].model || null);
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
		
		// Removed automatic hover-based linting to prevent unwanted messages
		/*
		monaco.languages.registerHoverProvider('python', {
			async provideHover(model: monaco.editor.ITextModel, position: monaco.Position, token: monaco.CancellationToken): Promise<monaco.languages.Hover | null> {
				if (selectedLanguage !== 'python') return null;

				try {
					const code = model.getValue();
					const response = await fetch('http://localhost:8000/lint', {
						method: 'POST',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify({ 
							code,
							line: position.lineNumber,
							column: position.column
						})
					});

					const lintResults = await response.json();
					
					// Format and display lint results in console
					let consoleOutput = '';
					if (lintResults.length === 0) {
						consoleOutput = '✅ No linting errors found';
					} else {
						consoleOutput = '🔍 Ruff found the following issues:\n\n';
						lintResults.forEach((error: any) => {
							consoleOutput += `Line ${error.line}, Column ${error.column}: ${error.message} (${error.code})\n`;
						});
					}
					consoleEditor.setValue(consoleOutput);

					return {
						diagnostics: lintResults.map((error: any) => ({
							severity: monaco.MarkerSeverity.Error,
							startLineNumber: error.line,
							startColumn: error.column,
							endLineNumber: error.line,
							endColumn: error.column + 1,
							message: error.message,
							code: error.code
						}))
					};
				} catch (error) {
					console.error('Linting failed:', error);
					consoleEditor.setValue('🔴 Error: Failed to run Ruff linter. Make sure the backend server is running.');
					return { diagnostics: [] };
				}
			}
		});
		*/

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
	<title>Mako</title>
</svelte:head>

<div class="flex-1 flex flex-col overflow-hidden">
	<div class="flex h-screen bg-[#1a1a1a]">
		<div class="w-[60%] flex flex-col flex-1" style="width: {isSidebarCollapsed ? '97%' : '60%'}; transition: all 0.3s ease-in-out;">
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
								class="opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity px-1"
								on:click|stopPropagation={() => removeFile(index)}
							>
								×
							</span>
						</button>
					{/each}
					<button
						on:click={addNewFile}
						class="px-3 py-1.5 bg-[#1a1a1a] text-gray-400 hover:bg-[#252525] border border-[#333333]"
					>
						+
					</button>
					
					<div class="flex-1"></div>
					
					<span class="text-gray-400 text-xs pr-2.5 font-mono">Press ⌘ + Enter to run</span>
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
		
		<div class="{isSidebarCollapsed ? 'w-[50px]' : 'w-[20%]'} border-l border-[#333333] flex flex-col bg-[#181818] p-4 relative transition-all duration-300 ease-in-out">
			<button
				class="absolute top-4 {isSidebarCollapsed ? 'left-1/2 -translate-x-1/2' : 'right-4'} text-gray-400 hover:text-white transition-colors"
				on:click={() => isSidebarCollapsed = !isSidebarCollapsed}
			>
				<svg 
					xmlns="http://www.w3.org/2000/svg" 
					class="h-5 w-5 transform transition-transform duration-300 {isSidebarCollapsed ? 'rotate-180' : ''}" 
					viewBox="0 0 24 24" 
					fill="none" 
					stroke="currentColor" 
					stroke-width="2" 
					stroke-linecap="round" 
					stroke-linejoin="round"
				>
					<circle cx="12" cy="12" r="1" />
					<circle cx="12" cy="5" r="1" />
					<circle cx="12" cy="19" r="1" />
				</svg>
			</button>

			<div class="right-panel h-full overflow-y-auto {isSidebarCollapsed ? 'opacity-0' : 'opacity-100'} transition-opacity duration-300" style="visibility: {isSidebarCollapsed ? 'hidden' : 'visible'}">
				<h2 class="text-white font-semibold mb-4 text-xs uppercase tracking-wider">Data Management</h2>
				<div class="space-y-4">
					<button
						class="w-full px-4 py-2 bg-[#181818] hover:bg-[#222222] text-white rounded-lg transition-colors text-sm flex items-center justify-center gap-2 border border-[#333333]"
						on:click={() => showDataImportModal = true}
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
							<polyline points="17 8 12 3 7 8" />
							<line x1="12" y1="3" x2="12" y2="15" />
						</svg>
						Import Data
					</button>

					<h2 
						class="text-white font-semibold mt-8 mb-4 text-xs uppercase tracking-wider flex items-center justify-between cursor-pointer hover:text-gray-300 transition-colors"
						on:click={() => isExploreExpanded = !isExploreExpanded}
					>
						<span>Local Datasets</span>
						<button 
							class="text-gray-400 hover:text-white transition-colors"
						>
							<svg 
								xmlns="http://www.w3.org/2000/svg" 
								class="h-4 w-4 transform transition-transform duration-200 {isExploreExpanded ? 'rotate-0' : '-rotate-90'}" 
								viewBox="0 0 24 24" 
								fill="none" 
								stroke="currentColor" 
								stroke-width="2" 
								stroke-linecap="round" 
								stroke-linejoin="round"
							>
								<polyline points="6 9 12 15 18 9"></polyline>
							</svg>
						</button>
					</h2>
					<div 
						class="space-y-1 overflow-hidden transition-all duration-200"
						style="max-height: {isExploreExpanded ? '500px' : '0px'}; opacity: {isExploreExpanded ? '1' : '0'}"
					>
						{#if datasets.length === 0}
							<div class="text-gray-400 text-sm p-1">
								No datasets available
							</div>
						{:else}
							{#each datasets as dataset}
								<div 
									class="flex items-center justify-between gap-2 text-gray-400 py-1 px-2 hover:bg-[#222222] rounded-lg transition-colors group"
								>
									<div 
										class="flex items-center gap-2 flex-1 cursor-pointer"
										on:click={() => addDatasetTab(dataset.name, dataset.path)}
									>
										<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
											<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
											<line x1="3" y1="9" x2="21" y2="9"/>
											<line x1="3" y1="15" x2="21" y2="15"/>
											<line x1="9" y1="9" x2="9" y2="21"/>
										</svg>
										<span class="text-sm">{dataset.name}</span>
									</div>
									<div class="dataset-dropdown relative">
										<button
											class="p-1 opacity-0 group-hover:opacity-100 hover:bg-[#333333] rounded transition-all"
											on:click|stopPropagation={() => showDropdownForDataset = showDropdownForDataset === dataset.path ? null : dataset.path}
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
												<circle cx="12" cy="12" r="1" />
												<circle cx="12" cy="5" r="1" />
												<circle cx="12" cy="19" r="1" />
											</svg>
										</button>
										
										{#if showDropdownForDataset === dataset.path}
											<div 
												class="fixed mt-1 w-48 bg-[#222222] rounded-lg shadow-lg border border-[#333333] z-[100]"
												style="left: calc(100% - 200px); transform: translateY(-50%);"
												on:click|stopPropagation
											>
												<button
													class="w-full px-4 py-2 text-sm text-left text-gray-400 hover:bg-[#333333] hover:text-white transition-colors flex items-center gap-2"
													on:click={() => analyzeDataset(dataset)}
												>
													<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
														<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
														<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
													</svg>
													Analyze Dataset
												</button>
												<button
													class="w-full px-4 py-2 text-sm text-left text-gray-400 hover:bg-[#333333] hover:text-white transition-colors flex items-center gap-2"
													on:click={() => {
														addDatasetContext(dataset);
														showDropdownForDataset = null;
													}}
												>
													<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
														<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
														<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
													</svg>
													Add Context
												</button>
												<button
													class="w-full px-4 py-2 text-sm text-left text-red-400 hover:bg-[#333333] hover:text-red-300 transition-colors flex items-center gap-2"
													on:click={() => {
														if (confirm('Are you sure you want to delete this dataset? This will also delete any associated context files.')) {
															deleteDataset(dataset.path);
														}
														showDropdownForDataset = null;
													}}
												>
													<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
														<path d="M3 6h18"></path>
														<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
														<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
													</svg>
													Delete Dataset
												</button>
											</div>
										{/if}
									</div>
								</div>
							{/each}
						{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<DataImportModal
	show={showDataImportModal}
	onClose={handleDataImportClose}
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
</style>