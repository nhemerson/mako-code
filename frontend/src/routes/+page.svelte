<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';

	let editor: Monaco.editor.IStandaloneCodeEditor;
	let consoleEditor: Monaco.editor.IStandaloneCodeEditor;
	let monaco: typeof Monaco;
	let editorContainer: HTMLElement;
	let consoleContainer: HTMLElement;
	let selectedLanguage = 'python';
	let resizing = false;
	let editorHeight = '70%';

	const languages = [
		{ id: 'python', name: 'Python' },
		{ id: 'sql', name: 'SQL' },
		{ id: 'rust', name: 'Rust' },
		{ id: 'javascript', name: 'JavaScript' }
	];

	const sampleCode = {
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

	function changeLanguage() {
		const model = editor.getModel();
		if (model) {
			monaco.editor.setModelLanguage(model, selectedLanguage);
			// Set sample code for the selected language
			editor.setValue(sampleCode[selectedLanguage] || '// Start coding here');
		}
	}

	async function executeCode() {
		const code = editor.getValue();
		let output = '';

		if (selectedLanguage === 'javascript' || selectedLanguage === 'typescript') {
			// Create a proxy console to capture output
			const proxyConsole = {
				log: (...args: any[]) => {
					output += args.map(arg => 
						typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
					).join(' ') + '\n';
				},
				error: (...args: any[]) => {
					output += '🔴 Error: ' + args.map(arg => 
						arg instanceof Error ? arg.message : String(arg)
					).join(' ') + '\n';
				},
				warn: (...args: any[]) => {
					output += '⚠️ Warning: ' + args.map(arg => String(arg)).join(' ') + '\n';
				}
			};

			try {
				const runCode = new Function('console', code);
				runCode(proxyConsole);
				consoleEditor.setValue(output || '// No output');
			} catch (error: any) {
				consoleEditor.setValue(`🔴 Error: ${error.message}`);
			}
		} else if (selectedLanguage === 'python') {
			try {
				consoleEditor.setValue('Running...');
				const response = await fetch('http://localhost:8000/execute', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
					},
					body: JSON.stringify({ code })
				});

				const result = await response.json();
				if (result.success) {
					consoleEditor.setValue(result.output || '// No output');
				} else {
					consoleEditor.setValue(`🔴 ${result.output}`);
				}
			} catch (error: any) {
				consoleEditor.setValue(`🔴 Error: Failed to execute code. Make sure the backend server is running.\n${error.message}`);
			}
		} else {
			consoleEditor.setValue(`🔴 Error: Running ${languages.find(l => l.id === selectedLanguage)?.name || selectedLanguage} code is not supported.\nCurrently supported yet.`);
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
				{ token: '', background: '1A1A1A' },
				{ token: 'keyword', foreground: '569CD6' },
				{ token: 'number', foreground: 'B5CEA8' },
			],
			colors: {
				'editor.background': '#1A1A1A',
				'editor.lineNumbers': '#858585',
				'editor.lineHighlightBackground': '#2A2A2A'
			}
		});

		editor = monaco.editor.create(editorContainer, {
			automaticLayout: true,
			theme: 'my-theme',
			minimap: {
				enabled: false
			},
			fontSize: 14,
			lineHeight: 24,
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
		
		const model = monaco.editor.createModel(
			sampleCode[selectedLanguage],
			selectedLanguage
		);
		editor.setModel(model);

		consoleEditor = monaco.editor.create(consoleContainer, {
			automaticLayout: true,
			theme: 'my-theme',
			minimap: {
				enabled: false
			},
			fontSize: 14,
			lineHeight: 24,
			readOnly: true,
			padding: {
				top: 16
			}
		});
		
		consoleEditor.setValue('// Console output will appear here');
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
</script>

<div class="flex-1 flex flex-col overflow-hidden">
	<div class="flex flex-col h-screen">
		<div class="w-full px-4 flex flex-col flex-1">
			<div class="flex justify-between items-center mb-2 pt-2.5">
				<div class="flex items-center space-x-4">
					<select
						bind:value={selectedLanguage}
						on:change={changeLanguage}
						class="bg-gray-800 text-white px-3 py-1.5 rounded-md border border-gray-600 focus:outline-none focus:border-blue-500"
					>
						{#each languages as lang}
							<option value={lang.id}>{lang.name}</option>
						{/each}
					</select>
				</div>
				<button 
					on:click={executeCode}
					class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md font-medium flex items-center space-x-2 transition-colors"
				>
					<span>▶</span>
					<span>Run Code</span>
				</button>
			</div>
			
			<div class="editors-container flex-1 flex flex-col pt-2.5">
				<div 
					class="editor-wrapper"
					style="height: {editorHeight}"
				>
					<div class="editor-container rounded-lg overflow-hidden border border-gray-700" bind:this={editorContainer} />
				</div>
				
				<div 
					class="resize-handle"
					on:mousedown={startResize}
				/>
				
				<div class="console-wrapper">
					<div class="console-container rounded-lg overflow-hidden border border-gray-700" bind:this={consoleContainer} />
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		background-color: #050505;
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
		background-color: #1A1A1A;
	}

	.resize-handle {
		height: 6px;
		background-color: #2A2A2A;
		border-top: 1px solid #404040;
		border-bottom: 1px solid #404040;
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
</style>