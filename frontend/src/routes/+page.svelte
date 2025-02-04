<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';

	let editor: Monaco.editor.IStandaloneCodeEditor;
	let consoleEditor: Monaco.editor.IStandaloneCodeEditor;
	let monaco: typeof Monaco;
	let editorContainer: HTMLElement;
	let consoleContainer: HTMLElement;
	let selectedLanguage: 'python' | 'sql' | 'rust' | 'javascript' = 'python';
	let resizing = false;
	let editorHeight = '80%';
	let output = '';

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
	}

	let files: EditorFile[] = [
		{ name: 'main.py', content: '# Python example\nprint("Hello World!")' },
	];
	let activeFileIndex = 0;
	let editingFileName = -1;

	function addNewFile() {
		const newFileName = `file${files.length + 1}.py`;
		files = [...files, { name: newFileName, content: '# New file' }];
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
		
		// Save current content
		if (editor && files[activeFileIndex]) {
			files[activeFileIndex].content = editor.getValue();
		}
		
		activeFileIndex = index;
		
		if (editor && files[activeFileIndex]) {
			if (!files[activeFileIndex].model) {
				files[activeFileIndex].model = monaco.editor.createModel(
					files[activeFileIndex].content,
					'python'
				);
			}
			editor.setModel(files[activeFileIndex].model || null);
		}
	}

	function removeFile(index: number) {
		// Don't allow removing the last file
		if (files.length <= 1) return;

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

		if (selectedLanguage === 'python') {
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
		} else if (selectedLanguage === 'javascript') {
			// Create a proxy console to capture output
			const proxyConsole = {
				log: (...args: any[]) => {
					const message = args.map(arg => 
						typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
					).join(' ') + '\n';
					output += message;
					console.log(...args);
				},
				error: (...args: any[]) => {
					const message = '🔴 Error: ' + args.map(arg => 
						arg instanceof Error ? arg.message : String(arg)
					).join(' ') + '\n';
					output += message;
					console.error(...args);
				},
				warn: (...args: any[]) => {
					const message = '⚠️ Warning: ' + args.map(arg => String(arg)).join(' ') + '\n';
					output += message;
					console.warn(...args);
				}
			};

			try {
				const runCode = new Function('console', code);
				runCode(proxyConsole);
				consoleEditor.setValue(output || '// No output');
				consoleEditor.revealLine(consoleEditor.getModel()?.getLineCount() || 1);
			} catch (error: any) {
				const errorMessage = `🔴 Error: ${error.message}`;
				consoleEditor.setValue(errorMessage);
				console.error(errorMessage);
				consoleEditor.revealLine(consoleEditor.getModel()?.getLineCount() || 1);
			}
		} else {
			const message = `🔴 Error: Running ${languages.find(l => l.id === selectedLanguage)?.name || selectedLanguage} code is not supported yet.`;
			consoleEditor.setValue(message);
			console.log(message);
			consoleEditor.revealLine(consoleEditor.getModel()?.getLineCount() || 1);
		}
	}

	onMount(async () => {
		monaco = (await import('./monaco')).default;

		// Register Python language features (keeping syntax highlighting)
		const { registerPythonCompletions } = await import('$lib/pythonLanguageFeatures');
		registerPythonCompletions(monaco);

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
				'editor.background': '#181818',
				'editor.foreground': '#D4D4D4',
				'editor.lineHighlightBackground': '#2F323B',
				'editor.selectionBackground': '#264F78',
				'editor.inactiveSelectionBackground': '#3A3D41',
				'editorLineNumber.foreground': '#858585',
				'editorLineNumber.activeForeground': '#C6C6C6',
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
			suggestOnTriggerCharacters: true,
			quickSuggestions: true,
			snippetSuggestions: 'inline',
		});
		
		// Add keyboard shortcut
		editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
			executeCode();
		});
		
		// Create model for initial file
		const model = monaco.editor.createModel(
			files[0].content,
			'python'
		);
		files[0].model = model;
		editor.setModel(files[0].model || null);

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
		// Register linting provider
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
	});

	onDestroy(() => {
		monaco?.editor.getModels().forEach((model: any) => model.dispose());
		editor?.dispose();
		consoleEditor?.dispose();
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
</script>

<div class="flex-1 flex flex-col overflow-hidden">
	<div class="flex h-screen">
		<div class="w-[80%] flex flex-col flex-1">
			<div class="flex flex-col">
				<div class="flex items-center space-x-0 pt-2.5 overflow-x-auto">
					{#each files as file, index}
						<button
							class="px-3 py-1.5 border-t border-l border-r border-[#333333] 
								   {index === activeFileIndex ? 'bg-[#181818] text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}
								   flex items-center min-w-[100px] max-w-[200px] group"
							on:click={() => switchFile(index)}
							on:mousedown={(e) => startRename(index, e)}
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
						class="px-3 py-1.5 bg-gray-800 text-gray-400 hover:bg-gray-700 border border-[#333333]"
					>
						+
					</button>
					
					<div class="flex-1"></div>
					
					<span class="text-gray-400 text-sm pr-2.5">Press ⌘ + Enter to run</span>
				</div>
			</div>
			
			<div class="editors-container flex-1 flex flex-col">
				<div 
					class="editor-wrapper"
					style="height: {editorHeight}"
				>
					<!-- svelte-ignore element_invalid_self_closing_tag -->
					<div class="editor-container" bind:this={editorContainer} />
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
		
		<div class="w-[20%] border-l border-[#333333] flex flex-col bg-[#181818] p-4">
			<div class="right-panel h-full overflow-y-auto">
				<h2 class="text-white font-semibold mb-4 text-xs">Right Panel</h2>
				<div class="text-gray-300 text-xs">
					<!-- Add your HTML content here -->
					<p class="mb-2">This is a regular HTML container where you can add any content.</p>
					<div class="bg-gray-800 p-3 rounded-md">
						<p>Sample content block</p>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		background-color: #181818;
	}

	.editors-container {
		position: relative;
		min-height: 0; /* Important for flex container */
	}

	.editor-wrapper {
		transition: height 0.05s ease;
	}

	.console-wrapper {
		flex: 1;
		min-height: 0; /* Important for flex container */
	}

	.editor-container, .console-container {
		height: 100%;
		width: 100%;
		background-color: #181818;
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