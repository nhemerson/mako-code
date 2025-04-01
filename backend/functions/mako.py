import os
from pathlib import Path
from typing import Union, List, Dict, Any
import polars as pl
from functions.ingestion import ensure_dataset_dir

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