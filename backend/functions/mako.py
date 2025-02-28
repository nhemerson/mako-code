import os
from pathlib import Path
from typing import Union, List, Dict, Any
import polars as pl
from functions.ingestion import ensure_dataset_dir
import re
from .sql_parser import parse_sql_code, validate_datasets
import json
import ast

# Get the absolute path to the backend directory
BACKEND_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_DIR = BACKEND_DIR / "data" / "local_storage"

def save(df: Union[pl.DataFrame, pl.LazyFrame], filename: str):
    """
    Save either a LazyFrame or DataFrame as a parquet file in the local storage directory.
    If given a LazyFrame, collects it first then saves. If given a DataFrame, saves directly.
    
    Args:
        df: The DataFrame or LazyFrame to save
        filename: Name for the saved file (without extension)
    Returns:
        The original DataFrame or LazyFrame for method chaining
    """
    # Ensure directory exists before trying to save
    ensure_dataset_dir()

    if not filename:
        print("Please provide a filename.")
        return df
            
    # Create full save path first
    save_path = DATASET_DIR / f'{filename}.parquet'
    # Create parent directories if they don't exist 
    save_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Saving file to: {save_path}")
    
    # Check if LazyFrame or DataFrame
    if isinstance(df, pl.LazyFrame):
        # Collect LazyFrame into DataFrame first
        df = df.collect()
        print(f"Collected LazyFrame to DataFrame: {df}")
        df.write_parquet(save_path)
    else:
        # Direct save for DataFrame
        df.write_parquet(save_path)
        
    print(f"File saved successfully. File exists: {save_path.exists()}")
    
    return df

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
    language: str
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
    if check_function_exists(name):
        return False, f"A function named '{name}' already exists"

    # Validate code if it's Python
    if language == 'python':
        code_valid, code_error = validate_python_function(code)
        if not code_valid:
            return False, code_error

    try:
        # Use absolute paths to avoid directory issues
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Create user_defined.py if it doesn't exist
        user_defined_path = os.path.join(base_dir, 'functions', 'user_defined.py')
        print(f"Checking for user_defined.py at: {user_defined_path}")
        
        if not os.path.exists(user_defined_path):
            print(f"Creating new user_defined.py file")
            with open(user_defined_path, 'w') as f:
                f.write("# User-defined functions\n\n")
        
        # Format the metadata as a docstring
        metadata_docstring = f'"""\n{description}\n\nTags: {", ".join(tags)}\nLanguage: {language}\n"""\n'
        
        # Append the new function with metadata
        print(f"Appending function to {user_defined_path}")
        with open(user_defined_path, 'a') as f:
            f.write(f'\n\n{metadata_docstring}{code}\n')
        
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
                
                lines = docstring.split('\n')
                if lines:
                    description = lines[0]
                
                for line in lines:
                    if line.startswith("Tags:"):
                        tags = [tag.strip() for tag in line[5:].split(',')]
                    elif line.startswith("Language:"):
                        language = line[9:].strip()
                
                functions.append({
                    'name': name,
                    'description': description,
                    'tags': tags,
                    'language': language
                })
        
        return functions
    except Exception as e:
        print(f"Error listing saved functions: {str(e)}")
        return []