import polars as pl
import os
import re
import ast
from typing import List, Dict, Any
from functions.mako import save
from functions.ingestion import DATASET_DIR
from functions.sql_parser import parse_sql_code, validate_datasets
from datetime import datetime

def execute_sql(code: str) -> pl.DataFrame:
    """
    Execute SQL code with support for saving results using Polars SQL context.
    
    Args:
        code: SQL code with optional save directive
        
    Returns:
        The result DataFrame
    """
    # Parse the SQL code
    sql_query, save_as, dataset_names = parse_sql_code(code)
    
    # Validate datasets exist
    is_valid, missing = validate_datasets(dataset_names, DATASET_DIR)
    if not is_valid:
        raise ValueError(f"Missing datasets: {', '.join(missing)}")
    
    # Create SQL context
    ctx = pl.SQLContext()
    
    # Load all required datasets and register them in the context
    for name in dataset_names:
        df = pl.read_parquet(DATASET_DIR / f"{name}.parquet")
        print(f"Loaded dataset: {name} (shape: {df.shape})")
        ctx.register(name, df)
    
    try:
        # Execute the query using SQL context
        result = ctx.execute(sql_query).collect()
        
        # Save results if requested
        if save_as:
            save(result, save_as)
            print(f"Results saved as: {save_as}")
        
        return result
    except Exception as e:
        raise ValueError(f"SQL execution error: {str(e)}")

def validate_python_function(code: str) -> tuple[bool, str]:
    """
    Validates if the provided code is a valid Python function.
    Returns (is_valid, error_message)
    """
    try:
        # Parse the code into an AST
        tree = ast.parse(code)
        
        # Check if the code contains at least one function definition
        has_function = any(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
        if not has_function:
            return False, "No function definition found in the code"
        
        # Try to compile the code to check for syntax errors
        compile(code, '<string>', 'exec')
        
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error: {str(e)}"
    except Exception as e:
        return False, f"Invalid code: {str(e)}"

def validate_function_name(name: str) -> tuple[bool, str]:
    """
    Validates if the function name follows Python naming conventions.
    Returns (is_valid, error_message)
    """
    if not name:
        return False, "Function name cannot be empty"
    
    # Check if name follows Python naming conventions
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        return False, "Invalid function name. Must start with a letter or underscore and contain only letters, numbers, and underscores"
    
    return True, ""

def check_function_exists(name: str) -> bool:
    """
    Checks if a function with the given name already exists in user_defined.py
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        user_defined_path = os.path.join(base_dir, 'functions', 'user_defined.py')
        
        if not os.path.exists(user_defined_path):
            return False
            
        with open(user_defined_path, 'r') as f:
            content = f.read()
            
        # Simple pattern matching for function definition
        pattern = rf"def\s+{name}\s*\("
        return bool(re.search(pattern, content))
    except Exception as e:
        print(f"Error checking if function exists: {str(e)}")
        return False

def save_function(
    name: str,
    code: str,
    description: str,
    tags: List[str],
    language: str,
    is_update: bool = False
) -> tuple[bool, str]:
    """
    Saves a function to user_defined.py with metadata as docstring.
    Returns (success, error_message)
    """
    # Validate function name
    name_valid, name_error = validate_function_name(name)
    if not name_valid:
        return False, name_error

    # Check if function already exists
    exists = check_function_exists(name)
    if exists and not is_update:
        return False, f"A function named '{name}' already exists"
    elif not exists and is_update:
        return False, f"Function '{name}' not found"

    # Validate code if it's Python
    if language == 'python':
        code_valid, code_error = validate_python_function(code)
        if not code_valid:
            return False, code_error

    try:
        # Use absolute paths to avoid directory issues
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        user_defined_path = os.path.join(base_dir, 'functions', 'user_defined.py')
        print(f"Checking for user_defined.py at: {user_defined_path}")
        
        # Create or clean up the file if needed
        if not os.path.exists(user_defined_path) or os.path.getsize(user_defined_path) == 0:
            with open(user_defined_path, 'w') as f:
                f.write("# User-defined functions\n\n")
        
        # Read the current content
        with open(user_defined_path, 'r') as f:
            content = f.read()
        
        # Parse the file to find all valid functions and imports
        tree = ast.parse(content)
        functions = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Get the import's code
                start_line = node.lineno
                end_line = node.end_lineno
                import_lines = content.splitlines()[start_line - 1:end_line]
                import_code = '\n'.join(import_lines)
                imports.append(import_code)
            elif isinstance(node, ast.FunctionDef):
                # Skip the function we're updating
                if node.name == name and is_update:
                    continue
                
                # Get the function's docstring and code
                docstring = ast.get_docstring(node) or ""
                start_line = node.lineno
                end_line = node.end_lineno
                
                # Get the function code
                func_lines = content.splitlines()[start_line - 1:end_line]
                func_code = '\n'.join(func_lines)
                
                # Add to our list of functions to keep
                functions.append((docstring, func_code))
        
        # Parse the new code to find any new imports
        new_tree = ast.parse(code)
        new_imports = []
        for node in ast.walk(new_tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Get the import's code
                start_line = node.lineno
                end_line = node.end_lineno
                import_lines = code.splitlines()[start_line - 1:end_line]
                import_code = '\n'.join(import_lines)
                new_imports.append(import_code)
        
        # Remove imports from the function code to avoid duplication
        code_lines = code.splitlines()
        filtered_code_lines = []
        i = 0
        while i < len(code_lines):
            line = code_lines[i]
            if not line.strip().startswith(('import ', 'from ')):
                filtered_code_lines.append(line)
            i += 1
        code = '\n'.join(filtered_code_lines)
        
        # Format the metadata as a docstring for the new/updated function
        metadata_docstring = f'"""\n{description}\n\nTags: {", ".join(tags)}\nLanguage: {language}\n"""'
        
        # Create new file content
        new_content = "# User-defined functions\n\n"
        
        # Add all unique imports at the top
        all_imports = list(set(imports + new_imports))
        if all_imports:
            new_content += '\n'.join(all_imports) + '\n\n'
        
        # Add all existing functions (except the one being updated)
        for func_docstring, func_code in functions:
            if func_docstring:
                new_content += f'\n{func_docstring}\n'
            new_content += f'\n{func_code}\n'
        
        # Add the new/updated function
        new_content += f'\n{metadata_docstring}\n{code}\n'
        
        # Write the file
        with open(user_defined_path, 'w') as f:
            f.write(new_content)
        
        print(f"Successfully wrote function code")
        return True, ""
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error saving function: {str(e)}\n{error_details}")
        return False, f"Failed to save function: {str(e)}"

def list_saved_functions() -> List[Dict[str, Any]]:
    """
    Returns a list of all saved functions with their metadata by parsing user_defined.py
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        user_defined_path = os.path.join(base_dir, 'functions', 'user_defined.py')
        
        if not os.path.exists(user_defined_path):
            return []
        
        with open(user_defined_path, 'r') as f:
            content = f.read()
        
        # Parse the Python file
        tree = ast.parse(content)
        
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Extract function name
                name = node.name
                
                # Extract docstring if available
                docstring = ast.get_docstring(node) or ""
                
                # Parse metadata from docstring
                description = ""
                tags = []
                language = "python"
                
                # Split docstring into lines and parse metadata
                lines = docstring.split('\n')
                if lines:
                    # First non-empty line is the description
                    description = next((line for line in lines if line.strip()), "")
                
                for line in lines:
                    if line.strip().startswith("Tags:"):
                        tags = [tag.strip() for tag in line[5:].split(',') if tag.strip()]
                    elif line.strip().startswith("Language:"):
                        language = line[9:].strip()
                
                # Get the function code
                start_line = node.lineno
                end_line = node.end_lineno
                code_lines = content.splitlines()[start_line - 1:end_line]
                function_code = '\n'.join(code_lines)
                
                functions.append({
                    'name': name,
                    'description': description,
                    'tags': tags,
                    'language': language,
                    'code': function_code,
                    'created_at': datetime.now().isoformat(),  # We don't track actual creation time
                    'updated_at': datetime.now().isoformat()
                })
        
        return functions
    except Exception as e:
        print(f"Error listing saved functions: {str(e)}")
        return []

def delete_function(name: str) -> tuple[bool, str]:
    """
    Deletes a function from user_defined.py
    Returns (success, error_message)
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        user_defined_path = os.path.join(base_dir, 'functions', 'user_defined.py')
        
        if not os.path.exists(user_defined_path):
            return False, "Functions file not found"
            
        with open(user_defined_path, 'r') as f:
            content = f.read()
            
        # Parse the file to find all functions
        tree = ast.parse(content)
        functions = []
        current_function = None
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get the function's docstring and code
                docstring = ast.get_docstring(node) or ""
                start_line = node.lineno
                end_line = node.end_lineno
                
                # Get the function code
                func_lines = content.splitlines()[start_line - 1:end_line]
                func_code = '\n'.join(func_lines)
                
                if node.name != name:  # Keep all functions except the one being deleted
                    functions.append((docstring, func_code))
                else:
                    current_function = node.name
        
        if not current_function:
            return False, f"Function '{name}' not found"
            
        # Create new file content
        new_content = "# User-defined functions\n\n"
        
        # Add all remaining functions
        for func_docstring, func_code in functions:
            if func_docstring:
                new_content += f'"""\n{func_docstring}\n"""\n'
            new_content += f'{func_code}\n\n'
        
        # Write the file
        with open(user_defined_path, 'w') as f:
            f.write(new_content.rstrip() + '\n')
        
        return True, ""
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error deleting function: {str(e)}\n{error_details}")
        return False, f"Failed to delete function: {str(e)}"