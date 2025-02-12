import os
from pathlib import Path
from typing import Union
import polars as pl
from functions.ingestion import ensure_dataset_dir
import re
from .sql_parser import parse_sql_code, validate_datasets

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