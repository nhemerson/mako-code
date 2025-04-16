from fastapi import FastAPI, HTTPException, UploadFile, Form, Query, Request, Response  # Needed for FastAPI functionality
from fastapi.middleware.cors import CORSMiddleware  # Needed for CORS middleware
from pydantic import BaseModel, Field, field_validator  # Needed for request validation
from io import StringIO  # Needed for handling in-memory file operations
import contextlib  # Needed for context management
import ast  # Needed for abstract syntax tree operations
import polars as pl  # Needed for data manipulation
from functions.ingestion import ensure_dataset_dir  # Needed to ensure dataset directory exists
import tempfile  # Needed for temporary file operations
from typing import List, Dict, Optional, Union  # Needed for type annotations
from pathlib import Path  # Needed for file path operations
import subprocess  # Needed for running subprocesses
import os  # Needed for operating system interactions
import functions.utils as utils
from dotenv import load_dotenv  # Needed for loading environment variables
from functions.utils import save_function  # Needed for saving functions
from datetime import datetime  # Needed for date and time operations
import json  # Needed for JSON operations

app = FastAPI(
    title="Mako API",
    description="Open Source Analytics Platform",
    version="0.1.0",
    docs_url="/api/docs" if os.getenv("ENVIRONMENT") == "development" else None,
    redoc_url=None
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://frontend:5173", "http://localhost:8001", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables from .env file
load_dotenv()

class CodeRequest(BaseModel):
    code: str = Field(..., description="Python code to execute")
    
    @field_validator('code')
    @classmethod
    def validate_code_safety(cls, v: str) -> str:
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
        'e', 'ceil', 'floor'
    ]
    SAFE_POLARS_FUNCTIONS: List[str] = ['*']  # Allow all Polars functions
    
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

# Add GCS and BigQuery modules to allowed modules
ALLOWED_EXTERNAL_MODULES = {
    'polars',
    'functions',
    'pyarrow',
    'bokeh',
    'sklearn',
    'matplotlib',
    'seaborn',
    'google.cloud'
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
                    # Allow standard library modules, polars, and GCS modules
                    module_name = name.name.split('.')[0]  # Get the root module name
                    if (module_name in STDLIB_MODULES or 
                        any(name.name.startswith(allowed) for allowed in ALLOWED_EXTERNAL_MODULES)):
                        continue
                    return False, f"Unsafe import detected: {name.name} - only standard library modules, polars and mako functions are allowed"
            if isinstance(node, ast.ImportFrom):
                # Allow standard library modules, polars, and GCS modules
                module_name = node.module.split('.')[0] if node.module else ''
                if (module_name in STDLIB_MODULES or 
                    any(node.module.startswith(allowed) for allowed in ALLOWED_EXTERNAL_MODULES)):
                    continue
                return False, f"Unsafe import detected: {node.module} - only standard library modules, polars and mako functions are allowed"
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
    """Create a dictionary of safe globals for code execution"""
    safe_globals = {}
    
    # Add polars module
    import polars as pl
    safe_globals['pl'] = pl
    safe_globals['polars'] = pl

    # Add os module
    import os
    safe_globals['os'] = os

    import pyarrow
    safe_globals['pyarrow'] = pyarrow

    import bokeh
    safe_globals['bokeh'] = bokeh

    # Add Google Cloud modules
    from google.cloud import storage, bigquery, bigquery_storage
    safe_globals['storage'] = storage
    safe_globals['bigquery'] = bigquery
    safe_globals['bigquery_storage'] = bigquery_storage

    # Add scikit-learn
    import sklearn
    safe_globals['sklearn'] = sklearn

    # Add matplotlib
    import matplotlib
    import matplotlib.pyplot as plt
    safe_globals['matplotlib'] = matplotlib
    safe_globals['plt'] = plt

    # Add seaborn
    import seaborn as sns
    safe_globals['seaborn'] = sns
    safe_globals['sns'] = sns

    # Add datetime module properly
    from datetime import datetime, timedelta, date, time, timezone
    safe_globals['datetime'] = datetime
    safe_globals['timedelta'] = timedelta
    safe_globals['date'] = date
    safe_globals['time'] = time
    safe_globals['timezone'] = timezone

    # Add random module properly
    import random
    safe_globals['random'] = random

    # Add functions.ingestion module with read_parquet
    from functions import mako
    safe_globals['functions'] = type('SafeMako', (), {
        'ingestion': type('SafeIngestion', (), {
            'read_parquet': pl.read_parquet
        }),
        'mako': mako
    })

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
    # First check if this is SQL code
    if request.code.strip().startswith('@sql'):
        try:
            # Execute SQL using mako function
            result = utils.execute_sql(request.code)
            return {
                "success": True,
                "output": str(result),
                "error_type": None
            }
        except ValueError as e:
            return {
                "success": False,
                "output": str(e),
                "error_type": "SQLError"
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Unexpected error executing SQL: {str(e)}",
                "error_type": "SQLError"
            }
    
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
        # Import the DATA_DIR constant from the ingestion module
        from functions.ingestion import DATA_DIR, ensure_dataset_dir
        
        # Use Path objects for consistent path handling
        data_root = Path(DATA_DIR)
        local_storage_path = data_root / "local_storage"
        cloud_storage_path = data_root / "cloud_storage"
        
        # Create directories if they don't exist
        ensure_dataset_dir()  # This handles the local_storage dir
        if not cloud_storage_path.exists():
            print(f"Creating directory: {cloud_storage_path}")
            cloud_storage_path.mkdir(parents=True, exist_ok=True)
        
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
            
            # Run Ruff using subprocess instead of the Python API
            result = subprocess.run(
                ["ruff", "check", "--format", "json", temp_file.name],
                capture_output=True,
                text=True
            )
            
            # Parse JSON output
            if result.stdout:
                import json
                findings = json.loads(result.stdout)
                diagnostics = []
                for finding in findings:
                    diagnostic = {
                        "line": finding.get("location", {}).get("row", 1),
                        "column": finding.get("location", {}).get("column", 1),
                        "message": f"{finding.get('message', '')} ({finding.get('code', 'E999')})",
                        "code": finding.get("code", "E999")
                    }
                    diagnostics.append(diagnostic)
                return diagnostics
            return []

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
        from functions.ingestion import DATASET_DIR
        file_path = DATASET_DIR / filename
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
        from functions.ingestion import DATA_DIR
        # Check multiple possible locations
        possible_paths = [
            Path(DATA_DIR) / filename,
            Path(DATA_DIR) / "local_storage" / filename
        ]
        
        exists = any(path.exists() for path in possible_paths)
        return {"exists": exists}
    except Exception as e:
        print(f"Error checking file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Initialize data directories
def init_data_directories():
    data_dirs = [
        Path("data"),
        Path("data/local_storage"),
        Path("data/cloud_storage"),
        Path("data/versions")  # Add versions directory
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
    """Delete a dataset and its context file from local storage"""
    try:
        # Get the filename from the path
        path = request["path"]
        if path.startswith("local_storage/"):
            path = path[len("local_storage/"):]
        
        # Construct the correct paths relative to the current directory
        file_path = Path("./data/local_storage") / path
        # Get the context file path by replacing .parquet with .md
        context_path = file_path.with_suffix('.md')
        
        print(f"Attempting to delete dataset at: {file_path}")
        print(f"Attempting to delete context at: {context_path}")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Dataset not found: {file_path}")
        
        # Delete both files
        file_path.unlink()
        if context_path.exists():
            context_path.unlink()
            
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save-dataset-context")
async def save_dataset_context(request: Request):
    data = await request.json()
    dataset_name = data.get("dataset_name")
    context_content = data.get("content")
    
    if not dataset_name or context_content is None:
        raise HTTPException(status_code=400, detail="Missing dataset name or content")
    
    try:
        context_path = Path("data/local_storage") / f"{dataset_name}.md"
        context_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(context_path, "w", encoding="utf-8") as f:
            f.write(context_content)
        
        return {"success": True, "message": "Context saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get-dataset-context/{dataset_name}")
async def get_dataset_context(dataset_name: str):
    try:
        context_path = Path("data/local_storage") / f"{dataset_name}.md"
        
        if not context_path.exists():
            return {"content": "", "exists": False}
        
        with open(context_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {"content": content, "exists": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DatasetRequest(BaseModel):
    path: str
    page: int
    rows_per_page: int

class DatasetResponse(BaseModel):
    success: bool
    data: List[Dict]
    columns: List[str]
    total_rows: int
    error: Optional[str] = None

@app.post("/api/get-dataset-data")
async def get_dataset_data(request: DatasetRequest) -> DatasetResponse:
    try:
        # Read the dataset
        df = pl.read_parquet(request.path)
        total_rows = len(df)
        
        # Calculate slice indices
        start_idx = (request.page - 1) * request.rows_per_page
        end_idx = start_idx + request.rows_per_page
        
        # Get the slice of data
        df_slice = df.slice(start_idx, request.rows_per_page)
        
        # Convert to dict format
        data = df_slice.to_dicts()
        columns = df.columns
        
        return DatasetResponse(
            success=True,
            data=data,
            columns=columns,
            total_rows=total_rows
        )
    except Exception as e:
        return DatasetResponse(
            success=False,
            data=[],
            columns=[],
            total_rows=0,
            error=str(e)
        )

@app.get("/api/get-dataset-schema/{dataset_name}")
async def get_dataset_schema(dataset_name: str):
    try:
        # Construct the path to the dataset
        dataset_path = f"./data/local_storage/{dataset_name}.parquet"
        
        # Read the dataset
        df = pl.read_parquet(dataset_path)
        
        # Get schema information
        schema = [
            {"column": col, "type": str(df.schema[col])}
            for col in df.columns
        ]
        
        return {"success": True, "schema": schema}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/get-context")
async def get_context(path: str):
    try:
        # Ensure we're looking in the local_storage directory
        if not path.startswith("data/local_storage/"):
            path = f"data/local_storage/{path}"
        
        context_path = Path(path)
        
        if not context_path.exists():
            return Response(status_code=404)
            
        with open(context_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UserFunction(BaseModel):
    """Model for user-defined functions"""
    name: str = Field(..., description="Name of the function")
    code: str = Field(..., description="The function code")
    description: str = Field(default="", description="Description of what the function does")
    tags: List[str] = Field(default_factory=list, description="List of tags for categorizing the function")
    language: str = Field(default="python", description="Programming language of the function")
    created_at: datetime = Field(default_factory=datetime.now, description="When the function was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When the function was last updated")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "example_function",
                "code": "def example_function(x: int) -> int:\n    return x * 2",
                "description": "A function that doubles its input",
                "tags": ["math", "utility"],
                "language": "python"
            }
        }

class SaveFunctionRequest(BaseModel):
    """Request model for saving a function"""
    name: str = Field(..., description="Name of the function")
    code: str = Field(..., description="The function code")
    description: str = Field(default="", description="Description of what the function does")
    tags: List[str] = Field(default_factory=list, description="List of tags for categorizing the function")
    language: str = Field(default="python", description="Programming language of the function")
    isUpdate: bool = Field(default=False, description="Whether this is an update to an existing function")

class SaveFunctionResponse(BaseModel):
    """Response model for save function endpoint"""
    success: bool
    error: Optional[str] = None
    function: Optional[UserFunction] = None

class ListFunctionsResponse(BaseModel):
    """Response model for list functions endpoint"""
    success: bool
    error: Optional[str] = None
    functions: List[UserFunction] = Field(default_factory=list)

@app.post("/api/save-function", response_model=SaveFunctionResponse)
async def save_user_function(data: SaveFunctionRequest):
    try:
        success, error = save_function(
            name=data.name,
            code=data.code,
            description=data.description,
            tags=data.tags,
            language=data.language,
            is_update=data.isUpdate
        )
        
        if success:
            # Create UserFunction instance with the saved data
            function = UserFunction(
                name=data.name,
                code=data.code,
                description=data.description,
                tags=data.tags,
                language=data.language
            )
            return SaveFunctionResponse(success=True, function=function)
        else:
            return SaveFunctionResponse(success=False, error=error)
    except Exception as e:
        return SaveFunctionResponse(success=False, error=str(e))

@app.get("/api/list-functions", response_model=ListFunctionsResponse)
async def list_functions():
    try:
        functions_data = utils.list_saved_functions()
        # Convert the raw function data to UserFunction instances
        functions = [
            UserFunction(
                name=func["name"],
                code=func.get("code", ""),  # Add code if available
                description=func.get("description", ""),
                tags=func.get("tags", []),
                language=func.get("language", "python"),
                created_at=func.get("created_at", datetime.now()),
                updated_at=func.get("updated_at", datetime.now())
            )
            for func in functions_data
        ]
        return ListFunctionsResponse(success=True, functions=functions)
    except Exception as e:
        return ListFunctionsResponse(success=False, error=str(e))

class VersionSaveRequest(BaseModel):
    """Request model for saving a code version"""
    code: str = Field(..., description="The code content to save")
    tab_name: str = Field(..., description="The name of the tab/file")
    execution_success: bool = Field(..., description="Whether the execution was successful")
    output: str = Field(default="", description="The execution output")
    
class VersionResponse(BaseModel):
    """Response model for version operations"""
    success: bool
    message: str
    version_path: Optional[str] = None
    error: Optional[str] = None

@app.post("/api/save-version", response_model=VersionResponse)
async def save_code_version(request: VersionSaveRequest):
    """Save a version of code with metadata"""
    try:
        # Create timestamp for version
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        
        # Sanitize tab name for folder name (replace invalid chars)
        sanitized_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in request.tab_name)
        sanitized_name = sanitized_name.strip()
        
        # Create versions directory structure
        versions_dir = Path("data/versions")
        versions_dir.mkdir(parents=True, exist_ok=True)
        
        tab_dir = versions_dir / sanitized_name
        tab_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if the code has changed from the previous version
        versions_metadata_path = tab_dir / "metadata.json"
        should_save = True
        
        if versions_metadata_path.exists():
            try:
                with open(versions_metadata_path, "r") as f:
                    metadata = json.load(f)
                    versions = metadata.get("versions", [])
                    
                    # If there are previous versions, check if code has changed
                    if versions:
                        latest_version = versions[-1]
                        latest_code_path = tab_dir / f"{latest_version['filename']}"
                        
                        if latest_code_path.exists():
                            with open(latest_code_path, "r") as code_file:
                                latest_code = code_file.read()
                                
                                # If code hasn't changed, don't save a new version
                                if latest_code == request.code:
                                    should_save = False
            except Exception as e:
                print(f"Error reading metadata: {str(e)}")
                # Continue with saving if there's an error reading metadata
                pass
        else:
            # Initialize metadata file
            metadata = {
                "tab_name": request.tab_name,
                "versions": []
            }
        
        if should_save:
            # Save the code file
            version_filename = f"{timestamp}.py"
            version_path = tab_dir / version_filename
            
            with open(version_path, "w") as f:
                f.write(request.code)
            
            # Create or update the metadata
            version_entry = {
                "timestamp": timestamp,
                "filename": version_filename,
                "execution_success": request.execution_success,
                "output_preview": request.output[:500] + "..." if len(request.output) > 500 else request.output
            }
            
            if not versions_metadata_path.exists():
                metadata = {
                    "tab_name": request.tab_name,
                    "versions": [version_entry]
                }
            else:
                with open(versions_metadata_path, "r") as f:
                    metadata = json.load(f)
                    metadata["versions"].append(version_entry)
            
            # Write back the updated metadata
            with open(versions_metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            return {
                "success": True,
                "message": "Version saved successfully",
                "version_path": str(version_path)
            }
        else:
            return {
                "success": True,
                "message": "No changes detected, version not saved"
            }
            
    except Exception as e:
        print(f"Error saving version: {str(e)}")
        return {
            "success": False,
            "message": "Failed to save version",
            "error": str(e)
        }

@app.post("/api/rename-version-folder")
async def rename_version_folder(request: dict):
    """Rename a version folder when a tab is renamed"""
    try:
        old_name = request.get("old_name")
        new_name = request.get("new_name")
        
        if not old_name or not new_name:
            return {
                "success": False,
                "message": "Missing old or new name",
                "error": "Both old_name and new_name are required"
            }
        
        # Sanitize names
        sanitized_old = "".join(c if c.isalnum() or c in "._- " else "_" for c in old_name).strip()
        sanitized_new = "".join(c if c.isalnum() or c in "._- " else "_" for c in new_name).strip()
        
        versions_dir = Path("data/versions")
        old_dir = versions_dir / sanitized_old
        new_dir = versions_dir / sanitized_new
        
        # Check if old directory exists
        if not old_dir.exists():
            return {
                "success": False,
                "message": f"Directory for {old_name} does not exist",
                "error": f"No version folder found for {old_name}"
            }
        
        # Check if new directory already exists
        if new_dir.exists():
            return {
                "success": False,
                "message": f"Directory for {new_name} already exists",
                "error": f"Cannot rename: {new_name} folder already exists"
            }
        
        # Rename directory
        old_dir.rename(new_dir)
        
        # Update metadata file if it exists
        metadata_path = new_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                metadata["tab_name"] = new_name
                
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        
        return {
            "success": True,
            "message": f"Renamed version folder from {old_name} to {new_name}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to rename version folder",
            "error": str(e)
        }

@app.get("/api/list-versions/{tab_name}")
async def list_versions(tab_name: str):
    """List all versions for a specific tab"""
    try:
        # Sanitize tab name
        sanitized_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in tab_name).strip()
        
        versions_dir = Path("data/versions")
        tab_dir = versions_dir / sanitized_name
        metadata_path = tab_dir / "metadata.json"
        
        if not metadata_path.exists():
            return {
                "success": False,
                "message": f"No versions found for {tab_name}",
                "versions": []
            }
        
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            
        return {
            "success": True,
            "message": f"Found {len(metadata.get('versions', []))} versions for {tab_name}",
            "versions": metadata.get("versions", [])
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to list versions",
            "error": str(e),
            "versions": []
        }

@app.get("/api/get-version/{tab_name}/{version_filename}")
async def get_version(tab_name: str, version_filename: str):
    """Get a specific version of code"""
    try:
        # Sanitize tab name
        sanitized_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in tab_name).strip()
        
        versions_dir = Path("data/versions")
        tab_dir = versions_dir / sanitized_name
        version_path = tab_dir / version_filename
        
        if not version_path.exists():
            return {
                "success": False,
                "message": f"Version {version_filename} not found for {tab_name}",
                "code": None
            }
        
        with open(version_path, "r") as f:
            code = f.read()
            
        return {
            "success": True,
            "message": f"Retrieved version {version_filename} for {tab_name}",
            "code": code
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to get version",
            "error": str(e),
            "code": None
        }

class DeleteFunctionResponse(BaseModel):
    """Response model for delete function endpoint"""
    success: bool
    error: Optional[str] = None

@app.delete("/api/delete-function/{name}", response_model=DeleteFunctionResponse)
async def delete_user_function(name: str):
    try:
        success, error = utils.delete_function(name)
        return DeleteFunctionResponse(success=success, error=error)
    except Exception as e:
        return DeleteFunctionResponse(success=False, error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 