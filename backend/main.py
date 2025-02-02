from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
from io import StringIO
import contextlib
import math
import ast
import polars as pl

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeRequest(BaseModel):
    code: str

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

@app.post("/execute")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 