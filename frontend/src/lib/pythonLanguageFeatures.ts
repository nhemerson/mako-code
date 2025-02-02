import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';

export function registerPythonCompletions(monaco: typeof Monaco) {
    monaco.languages.registerCompletionItemProvider('python', {
        provideCompletionItems: (model, position) => {
            const suggestions = [
                {
                    label: 'print',
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'print(${1})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Print a message to the console'
                },
                {
                    label: 'def',
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'def ${1:function_name}(${2:parameters}):\n\t${3:pass}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Define a new function'
                },
                {
                    label: 'if',
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'if ${1:condition}:\n\t${2:pass}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'If statement'
                },
                {
                    label: 'for',
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'for ${1:item} in ${2:items}:\n\t${3:pass}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'For loop'
                },
                {
                    label: 'while',
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'while ${1:condition}:\n\t${2:pass}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'While loop'
                },
                {
                    label: 'class',
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'class ${1:ClassName}:\n\tdef __init__(self):\n\t\t${2:pass}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Define a new class'
                },
                {
                    label: 'import',
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'import ${1:module}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Import a module'
                },
                {
                    label: 'from',
                    kind: monaco.languages.CompletionItemKind.Keyword,
                    insertText: 'from ${1:module} import ${2:name}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Import specific items from a module'
                },
                // Polars suggestions
                {
                    label: 'import polars',
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'import polars as pl',
                    documentation: 'Import polars library'
                },
                {
                    label: 'pl.DataFrame',
                    kind: monaco.languages.CompletionItemKind.Constructor,
                    insertText: 'pl.DataFrame(${1:data})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create a new Polars DataFrame'
                },
                {
                    label: 'pl.from_dict',
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'pl.from_dict({\n\t"${1:column}": [${2:values}]\n})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    documentation: 'Create DataFrame from dictionary'
                }
            ];

            return { suggestions };
        }
    });
} 