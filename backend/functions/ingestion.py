import polars as pl
import json
import os
import io
from pathlib import Path
from fastapi import UploadFile
from typing import Union

# Get the absolute path to the backend directory
BACKEND_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_DIR = BACKEND_DIR / "data" / "local_storage"

def ensure_dataset_dir():
    """Ensure the datasets directory exists"""
    try:
        DATASET_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Dataset directory ensured at: {DATASET_DIR}")
    except Exception as e:
        print(f"Error creating dataset directory: {e}")

async def process_uploaded_file(file: UploadFile, new_filename: str) -> dict:
    """
    Process an uploaded file (JSON, CSV, or Parquet) and save it as a Parquet file using Polars.
    
    Args:
        file: The uploaded file
        new_filename: The desired name for the saved file (without extension)
    
    Returns:
        dict: Status of the operation
    """
    ensure_dataset_dir()
    
    # Read the file content
    content = await file.read()
    file_extension = file.filename.split('.')[-1].lower()
    
    try:
        if file_extension == 'json':
            # Handle JSON file
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            data = json.loads(content)
            # Convert JSON to Polars DataFrame
            if isinstance(data, list):
                df = pl.DataFrame(data)
            else:
                # If it's a dict, we need to handle it differently
                df = pl.DataFrame([data])
        
        elif file_extension == 'csv':
            # Handle CSV file
            df = pl.read_csv(io.BytesIO(content))
        
        elif file_extension == 'parquet':
            # Handle Parquet file
            df = pl.read_parquet(io.BytesIO(content))
        
        else:
            return {
                "success": False,
                "error": f"Unsupported file type: {file_extension}"
            }
        
        # Save as parquet
        output_path = DATASET_DIR / f"{new_filename}.parquet"
        print(f"Saving file to: {output_path}")
        df.write_parquet(output_path)
        print(f"File saved successfully. File exists: {output_path.exists()}")
        
        return {
            "success": True,
            "message": "File processed and saved successfully",
            "filename": f"{new_filename}.parquet",
            "path": str(output_path)
        }
    
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

