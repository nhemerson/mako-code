from fastapi import FastAPI, HTTPException, UploadFile, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import sys
from io import StringIO
import contextlib
import math
import ast
import polars as pl
from functions_mako.ingestion import process_uploaded_file, DATASET_DIR
import ruff
import tempfile
from typing import List, Dict, Optional, Union
from pathlib import Path
import subprocess
import os

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # SvelteKit dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeRequest(BaseModel):
    code: str = Field(..., description="Python code to execute")
    
    @validator('code')
    def validate_code_safety(cls, v):
        # Instead of raising an error, return the code
        # The safety check will be done in the endpoint
        return v

class UploadRequest(BaseModel):
    newFileName: str = Field(..., description="Name for the uploaded file")

class ExecutionResponse(BaseModel):
    success: bool
    output: str
    error_type: Optional[str] = None

class UploadResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    filename: Optional[str] = None
    fileExists: bool

class ParquetData(BaseModel):
    success: bool
    data: List[Dict]
    rows: int
    columns: int

class LintDiagnostic(BaseModel):
    line: int
    column: int
    message: str
    code: str

class LintRequest(BaseModel):
    code: str
    line: Optional[int] = None  # Make line optional
    column: Optional[int] = None  # Make column optional

class Settings(BaseModel):
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]
    SAFE_MATH_FUNCTIONS: List[str] = [
        'sqrt', 'pow', 'sin', 'cos', 'tan', 'pi', 
        'e', 'ceil', 'floor', 'abs'
    ]
    SAFE_POLARS_FUNCTIONS: List[str] = [
        'DataFrame', 'Series', 'concat', 'col', 'lit',
        'sum', 'mean', 'min', 'max', 'count', 'std', 'var',
        'struct', 'from_dict', 'from_records', 'date_range',
        'scan_csv', 'select', 'when', 'arange'
    ]
    
    class Config:
        env_file = ".env"

settings = Settings()

# Standard library modules list
STDLIB_MODULES = {
    'abc', 'argparse', 'array', 'ast', 'asyncio', 'base64', 'binascii', 'bisect', 
    'calendar', 'collections', 'concurrent', 'contextlib', 'copy', 'csv', 'datetime', 
    'decimal', 'difflib', 'duckdb', 'enum', 'fileinput', 'fnmatch', 'fractions', 'functools', 
    'glob', 'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib', 'imghdr', 
    'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword', 'linecache', 
    'locale', 'logging', 'math', 'mimetypes', 'numbers', 'operator', 'os', 'pathlib', 
    'pickle', 'pickletools', 'platform', 'pprint', 'queue', 'random', 're', 'reprlib', 
    'secrets', 'selectors', 'shelve', 'shlex', 'shutil', 'signal', 'socket', 'socketserver', 
    'statistics', 'string', 'struct', 'subprocess', 'sys', 'tempfile', 'textwrap', 'threading', 
    'time', 'timeit', 'token', 'tokenize', 'traceback', 'types', 'typing', 'unicodedata', 
    'unittest', 'urllib', 'uuid', 'warnings', 'wave', 'weakref', 'xml', 'xmlrpc', 'zipfile', 'zlib'
}

def is_safe_code(code: str) -> tuple[bool, str]:
    """Check if the code is safe to execute and return detailed error messages."""
    try:
        # First check basic syntax
        tree = ast.parse(code)
        for node in ast.walk(tree):
            # Check for unsafe imports
            if isinstance(node, ast.Import):
                for name in node.names:
                    # Allow polars and any module from Python's standard library
                    if name.name == 'polars' or name.name in STDLIB_MODULES:
                        continue
                    return False, f"Unsafe import detected - only standard library modules and polars are allowed"
            if isinstance(node, ast.ImportFrom):
                # Allow polars and any module from Python's standard library
                if node.module == 'polars' or node.module in STDLIB_MODULES:
                    continue
                return False, f"Unsafe import detected - only standard library modules and polars are allowed"
            # Check for unsafe calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec']:
                        return False, f"Unsafe function call detected: {node.func.id}"
        
        # Run Ruff linter for additional checks
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file.flush()
            
            try:
                result = subprocess.run(
                    ["ruff", "check", temp_file.name], 
                    capture_output=True, 
                    text=True
                )
                if result.returncode != 0:
                    # Get the first error message
                    error_lines = result.stdout.strip().split('\n')
                    if error_lines:
                        return False, error_lines[0]
            finally:
                # Clean up temp file
                os.unlink(temp_file.name)

        return True, ""
    except SyntaxError as se:
        return False, f"Syntax error: {str(se)}"
    except Exception as e:
        return False, f"Code validation error: {str(e)}"

def create_safe_globals():
    """Create a dictionary of safe functions and modules."""
    safe_globals = {}
    
    # Add all standard library modules
    for module_name in STDLIB_MODULES:
        try:
            module = __import__(module_name)
            safe_globals[module_name] = module
        except ImportError:
            continue

    # Create a dictionary for polars safe functions
    safe_polars = {
        'DataFrame': pl.DataFrame,
        'Series': pl.Series,
        'concat': pl.concat,
        'col': pl.col,
        'lit': pl.lit,
        'sum': pl.sum,
        'mean': pl.mean,
        'min': pl.min,
        'max': pl.max,
        'count': pl.count,
        'std': pl.std,
        'var': pl.var,
        'struct': pl.struct,
        'from_dict': pl.from_dict,
        'from_records': pl.from_records,
        'date_range': pl.date_range,
        'scan_csv': pl.scan_csv,
        'select': pl.select,
        'when': pl.when,
        'arange': pl.arange,
    }

    # Add polars module
    safe_globals['polars'] = safe_polars
    safe_globals['pl'] = safe_polars  # Allow both 'polars' and 'pl' as module names

    # Add DuckDB module
    import duckdb
    safe_globals['duckdb'] = duckdb

    # Add built-in functions
    safe_globals.update({
        'abs': abs,
        'all': all,
        'any': any,
        'bool': bool,
        'dict': dict,
        'enumerate': enumerate,
        'filter': filter,
        'float': float,
        'format': format,
        'frozenset': frozenset,
        'int': int,
        'isinstance': isinstance,
        'len': len,
        'list': list,
        'map': map,
        'max': max,
        'min': min,
        'print': print,
        'range': range,
        'repr': repr,
        'reversed': reversed,
        'round': round,
        'set': set,
        'slice': slice,
        'sorted': sorted,
        'str': str,
        'sum': sum,
        'tuple': tuple,
        'zip': zip,
    })

    return safe_globals

@app.post("/execute", response_model=ExecutionResponse)
async def execute_code(request: CodeRequest):
    # First check code safety
    is_safe, error_msg = is_safe_code(request.code)
    if not is_safe:
        return {
            "success": False,
            "output": error_msg,
            "error_type": "CodeValidationError"
        }

    try:
        # Create string buffer to capture output
        stdout = StringIO()
        stderr = StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                # Create safe globals and locals
                safe_globals = create_safe_globals()
                local_vars = {}

                # Execute the code
                exec(compile(request.code, '<string>', 'exec'), safe_globals, local_vars)
                
                # Get the output
                output = stdout.getvalue().strip()
                error = stderr.getvalue().strip()
                
                if error:
                    return {
                        "success": False, 
                        "output": error,
                        "error_type": "RuntimeError"
                    }
                
                # Return meaningful message if no output
                if not output:
                    return {
                        "success": True, 
                        "output": "Code executed successfully (no output)",
                        "error_type": None
                    }
                    
                return {
                    "success": True, 
                    "output": output,
                    "error_type": None
                }
                
            except Exception as e:
                error_type = type(e).__name__
                return {
                    "success": False, 
                    "output": str(e),
                    "error_type": error_type
                }
    
    except Exception as e:
        return {
            "success": False,
            "output": str(e),
            "error_type": type(e).__name__
        }

@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile,
    newFileName: str = Form(...)
):
    try:
        # Use relative paths from current directory (backend)
        data_root = Path("./data")
        local_storage_path = data_root / "local_storage"
        cloud_storage_path = data_root / "cloud_storage"
        
        # Create directories if they don't exist
        for path in [data_root, local_storage_path, cloud_storage_path]:
            if not path.exists():
                print(f"Creating directory: {path}")
                path.mkdir(parents=True, exist_ok=True)
        
        # Check if file already exists
        output_path = local_storage_path / f"{newFileName}.parquet"
        file_exists = output_path.exists()
        
        # Read the file content based on its type
        content = await file.read()
        file_extension = file.filename.split('.')[-1].lower()
        
        # Create a temporary file to store the content
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            # Write content as bytes
            temp_file.write(content)
            temp_file.flush()
            temp_path = Path(temp_file.name)
            
            try:
                # Convert to parquet based on file type
                if file_extension == 'csv':
                    df = pl.read_csv(temp_path)
                elif file_extension == 'json':
                    df = pl.read_json(temp_path)
                elif file_extension == 'parquet':
                    df = pl.read_parquet(temp_path)
                elif file_extension in ['arrow', 'ipc', 'feather']:  # Support multiple Arrow format extensions
                    df = pl.read_ipc(temp_path)  # IPC is the format for Arrow files
                else:
                    raise ValueError(f"Unsupported file type: {file_extension}")
                
                # Save as parquet
                print(f"Saving parquet file to: {output_path}")
                df.write_parquet(output_path)
                
                return {
                    "success": True,
                    "filename": f"{newFileName}.parquet",
                    "error": None,
                    "fileExists": file_exists
                }
            finally:
                # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink()
        
    except Exception as e:
        print(f"Error during file upload: {str(e)}")
        return {
            "success": False,
            "filename": None,
            "error": str(e),
            "fileExists": False
        }

@app.get("/api/read-parquet", response_model=ParquetData)
async def read_parquet(filename: str = Query(...)):
    """
    Read a parquet file and return its contents
    """
    try:
        print(f"Attempting to read parquet file: {filename}")
        file_path = DATASET_DIR / filename
        print(f"Full file path: {file_path}")
        print(f"File exists: {file_path.exists()}")
        
        if not file_path.exists():
            print(f"File not found at path: {file_path}")
            raise HTTPException(status_code=404, detail=f"File {filename} not found at {file_path}")
        
        try:
            # Read the parquet file
            df = pl.read_parquet(file_path)
            print(f"Successfully read parquet file with shape: {df.shape}")
            
            # Convert to list of dictionaries for JSON serialization
            data = df.to_dicts()
            print(f"Successfully converted to dictionary format with {len(data)} rows")
            
            return {
                "success": True,
                "data": data,
                "rows": len(data),
                "columns": len(data[0]) if data else 0
            }
        except Exception as e:
            print(f"Error reading parquet file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error reading parquet file: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/lint", response_model=List[LintDiagnostic])
async def lint_code(request: LintRequest):
    try:
        # First check for syntax errors
        try:
            ast.parse(request.code)
        except SyntaxError as se:
            return [{
                "line": se.lineno or 1,
                "column": se.offset or 1,
                "message": f"Syntax error: {str(se)}",
                "code": "E999"
            }]
            
        # Create a temporary file for Ruff to analyze
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as temp_file:
            temp_file.write(request.code)
            temp_file.flush()
            
            # Run Ruff linter
            linter = ruff.Linter()
            results = linter.lint(Path(temp_file.name))
            
            # Format the results
            diagnostics = []
            for result in results:
                diagnostic = {
                    "line": result.location.row,
                    "column": result.location.column,
                    "message": f"{result.violation_message or result.message} ({result.code})",
                    "code": result.code
                }
                diagnostics.append(diagnostic)
            
            return diagnostics

    except Exception as e:
        return [{
            "line": 1,
            "column": 1,
            "message": f"Linting error: {str(e)}",
            "code": "E999"
        }]

@app.get("/api/check-file")
async def check_file_exists(filename: str = Query(...)):
    """
    Check if a file exists in the local storage
    """
    try:
        file_path = Path("data/local_storage") / filename
        return {
            "exists": file_path.exists()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dataset")
async def get_dataset(path: str):
    try:
        # Check multiple possible locations for the dataset
        possible_paths = [
            os.path.join("data", path),
            os.path.join("data", "local_storage", path)
        ]
        
        found_path = None
        for test_path in possible_paths:
            print(f"Checking path: {test_path}")
            if os.path.exists(test_path):
                found_path = test_path
                break
        
        if not found_path:
            print(f"Dataset not found in any of these locations: {possible_paths}")
            raise HTTPException(
                status_code=404, 
                detail=f"Dataset not found in any of these locations: {possible_paths}"
            )
        
        print(f"Loading dataset from: {found_path}")
        # Read the dataset
        df = pl.read_parquet(found_path)
        
        # Convert to a format suitable for JSON serialization
        # Limit to first 1000 rows for performance
        data = df.head(1000).to_dicts()
        columns = df.columns
        
        print(f"Successfully loaded dataset with {len(data)} rows and {len(columns)} columns")
        return {
            "data": data,
            "columns": columns
        }
    except Exception as e:
        print(f"Error loading dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/check-file")
async def check_file(filename: str):
    try:
        # Check multiple possible locations
        possible_paths = [
            os.path.join("data", filename),
            os.path.join("data", "local_storage", filename)
        ]
        
        exists = any(os.path.exists(path) for path in possible_paths)
        return {"exists": exists}
    except Exception as e:
        print(f"Error checking file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Initialize data directories
def init_data_directories():
    data_dirs = [
        Path("data"),
        Path("data/local_storage"),
        Path("data/cloud_storage")
    ]
    for dir_path in data_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Ensuring directory exists: {dir_path}")

# Call this when the app starts
init_data_directories()

@app.get("/api/list-datasets")
async def list_datasets():
    """List all available datasets in the local storage"""
    try:
        datasets = []
        local_storage = Path("./data/local_storage")
        for file in local_storage.glob("*.parquet"):
            datasets.append({
                "name": file.stem,
                "path": f"local_storage/{file.name}",
                "size": file.stat().st_size,
                "modified": file.stat().st_mtime
            })
        return {"datasets": datasets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/delete-dataset")
async def delete_dataset(request: dict):
    """Delete a dataset from local storage"""
    try:
        # Get the filename from the path
        path = request["path"]
        if path.startswith("local_storage/"):
            path = path[len("local_storage/"):]
        
        # Construct the correct path relative to the current directory
        file_path = Path("./data/local_storage") / path
        print(f"Attempting to delete file at: {file_path}")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Dataset not found: {file_path}")
        
        file_path.unlink()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 