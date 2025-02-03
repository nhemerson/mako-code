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
        if not is_safe_code(v):
            raise ValueError("Code contains unsafe operations")
        return v

class UploadRequest(BaseModel):
    newFileName: str = Field(..., description="Name for the uploaded file")

class ExecutionResponse(BaseModel):
    success: bool
    output: str

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

def is_safe_code(code: str) -> bool:
    """Check if the code is safe to execute."""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            # Allow imports for math and polars
            if isinstance(node, ast.Import):
                if any(name.name not in ['math', 'polars'] for name in node.names):
                    return False
            if isinstance(node, ast.ImportFrom):
                if node.module not in ['math', 'polars']:
                    return False
            # Prevent file operations
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['open', 'eval', 'exec']:
                        return False
        return True
    except:
        return False

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
    try:
        if not is_safe_code(request.code):
            return {"success": False, "output": "Error: Code contains unsafe operations"}

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
                output = stdout.getvalue()
                error = stderr.getvalue()
                
                if error:
                    return {"success": False, "output": error}
                return {"success": True, "output": output or "// No output"}
                
            except Exception as e:
                return {"success": False, "output": f"Error: {str(e)}"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
async def lint_code(data: CodeRequest):
    code = data.code
    try:
        # Create a temporary file for Ruff to analyze
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as tmp:
            tmp.write(code)
            tmp.flush()
            
            # Run Ruff
            result = ruff.check([tmp.name])
            
            # Convert results to JSON-serializable format
            diagnostics = []
            for error in result:
                diagnostics.append({
                    "line": error.location.row,
                    "column": error.location.column,
                    "message": error.message,
                    "code": error.code
                })
            
            return diagnostics
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 