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

def scan_parquet(file_path: Union[str, Path]) -> pl.LazyFrame:
    """
    Wrapper for pl.scan_parquet that adds a save method to save locally.
    
    Args:
        file_path: Path to the parquet file to scan
        
    Returns:
        LazyFrame with added save method
    """
    # Get the base lazy frame
    lf = pl.scan_parquet(file_path)
    
    # Add save method
    def save(self, filename: str):
        """
        Save the LazyFrame as a parquet file in the local storage directory.
        First collects the LazyFrame into an eager DataFrame, then saves.
        
        Args:
            filename: Name for the saved file (without extension)
        """
        # Ensure directory exists before trying to save
        ensure_dataset_dir()

        if filename:
            # Create full save path first
            save_path = DATASET_DIR / f'{filename}.parquet'
            # Create parent directories if they don't exist 
            save_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"Saving file to: {save_path}")
        else:
            print("Please provide a filename.")
            return
        
        # Collect the LazyFrame into an eager DataFrame
        df = self.collect()

        print(f"Collected DataFrame: {df}")
        
        # Save the eager DataFrame
        df.write_parquet(save_path)
        print(f"File saved successfully. File exists: {save_path.exists()}")
        
    # Attach save method to lazy frame
    lf.save = save.__get__(lf)
    
    return lf


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

# Save Report Name Locally
        
def get_saved_report(report_name: str) -> dict:
    """
    Retrieves the saved report parameters from a JSON file.

    Args:
        report_name (str): The name of the report.

    Returns:
        dict: The saved report parameters as a dictionary.

    Raises:
        FileNotFoundError: If the JSON file is not found.

    """
    try:
        with open(f'./data/report_params/{report_name}.json', 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        return None