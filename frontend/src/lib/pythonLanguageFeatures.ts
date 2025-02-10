import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';

export function registerPythonCompletions(monaco: any) {
    // Create a set to track added suggestions
    const addedSuggestions = new Set();
    
    monaco.languages.registerCompletionItemProvider('python', {
        provideCompletionItems: (model: any, position: any) => {
            const suggestions: Monaco.languages.CompletionItem[] = [];
            const word = model.getWordUntilPosition(position);
            const range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: word.startColumn,
                endColumn: word.endColumn
            };

            // Common Python imports
            const imports = ['import', 'from', 'as'];
            const commonModules = ['polars'];

            // Only add suggestions that haven't been added yet
            [...imports, ...commonModules].forEach(item => {
                if (!addedSuggestions.has(item)) {
                    suggestions.push({
                        label: item,
                        kind: monaco.languages.CompletionItemKind.Keyword,
                        insertText: item,
                        range: range
                    });
                    addedSuggestions.add(item);
                }
            });

            return { suggestions };
        }
    });
} 