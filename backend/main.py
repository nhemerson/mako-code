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
        # ... other functions ...
    ]
    
    class Config:
        env_file = ".env"

settings = Settings()

def is_safe_code(code: str) -> tuple[bool, str]:
    """Check if the code is safe to execute and return detailed error messages."""
    try:
        # First check basic syntax
        tree = ast.parse(code)
        for node in ast.walk(tree):
            # Check for unsafe imports
            if isinstance(node, ast.Import):
                if any(name.name not in ['math', 'polars'] for name in node.names):
                    return False, "Unsafe import detected - only math and polars modules are allowed"
            if isinstance(node, ast.ImportFrom):
                if node.module not in ['math', 'polars']:
                    return False, "Unsafe import detected - only math and polars modules are allowed"
            # Check for unsafe calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['open', 'eval', 'exec']:
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
    # Create a dictionary for the math module's safe functions
    safe_math = {}
    for name in ['sqrt', 'pow', 'sin', 'cos', 'tan', 'pi', 'e', 'ceil', 'floor', 'abs']:
        if hasattr(math, name):
            safe_math[name] = getattr(math, name)

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

    return {
        'math': safe_math,
        'polars': safe_polars,
        'pl': safe_polars,  # Allow both 'polars' and 'pl' as module names
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
    }

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
    request: UploadRequest
):
    """
    Handle file upload and conversion to parquet
    """
    result = await process_uploaded_file(file, request.newFileName)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 