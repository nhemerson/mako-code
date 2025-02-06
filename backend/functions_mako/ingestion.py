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
    def save(filename: str):
        """
        Save the LazyFrame as a parquet file in the local storage directory.
        
        Args:
            filename: Name for the saved file (without extension)
        """
        # Ensure directory exists before trying to save
        ensure_dataset_dir()
            
        # Create full save path
        save_path = DATASET_DIR / f'{filename}.parquet'
        
        # Create parent directories if they don't exist
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Collect and save
        lf.collect().write_parquet(save_path)
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

  
# Create a local delta table
def create_delta_table(dataframe: pl.DataFrame, delta_table_name: str, partition_by: str = "None", partition_range: str = "None", write_mode: str = "None") -> pl.DataFrame:
    """
    Creates a local delta table based on the provided dataframe.

    Args:
        dataframe (pl.DataFrame): The dataframe to create the delta table from.
        delta_table_name (str): The name of the delta table.
        partition_by (str): The column to partition the delta table by.
        partition_range (str): The range of partitioning (None, Day, or Month).
        write_mode (str): The save mode for the delta table.

    Returns:
        pl.DataFrame: The created delta table as a polars dataframe.

    Raises:
        Exception: If there is an error creating the delta table.

    """
    # Read in dataframe to polars datframe
    df_polars_collect = dataframe
    print(f"{delta_table_name} dataframe read")
    print(partition_range)

    # check if partition_by column passsed is a date unless none
    if partition_range == "None":
        try:
            df_polars_collect_none = df_polars_collect
            print(f"Dataframe for {partition_range} created for {delta_table_name}")
        except Exception as e: 
            print(f"Couldn't make delta table with {partition_by}")
            return pl.DataFrame()
    elif partition_range == "Day":
        try:
            df_polars_collect_day = df_polars_collect.with_columns(pl.col(partition_by).dt.date().alias("created_date"))
            print(f"created_date column created from {partition_by} for {delta_table_name}")
        except Exception as e: 
            print(f"Couldn't make delta table with {partition_by} column")
            return pl.DataFrame()
    elif partition_range == "Month":
        try:
            df_polars_collect_month = df_polars_collect.with_columns(pl.col(partition_by).dt.month().alias("created_month"))
            print(f"created_month column created from {partition_by} for {delta_table_name}")
        except Exception as e: 
            print(f"Couldn't make delta table with {partition_by} column")
            return pl.DataFrame()
    else:
        print(f"Couldn't make delta table with {partition_range} range")
        return pl.DataFrame()
    
    # Source for delta table destination folder
    delta_table_uri = f"./data/delta_tables/{delta_table_name}/"
    print(f"{delta_table_name} delta table uri created: {delta_table_uri}")

    # Create delta table based on partition range
    if partition_range == "None":
        try:
            if write_mode.lower() == "none":
                print(f"If no error message, {delta_table_name} delta table created!")
                df_polars_collect_none.write_delta(delta_table_uri, mode="error")
            else:
                print(f"If no error message, {delta_table_name} delta table created!")
                df_polars_collect_none.write_delta(delta_table_uri, mode=write_mode.lower())
        except Exception as e: 
            return pl.DataFrame()
    elif partition_range == "Day":
        try:
            if write_mode.lower() == "none":
                print(f"If no error message, {delta_table_name} delta table created!")
                df_polars_collect_day.write_delta(delta_table_uri, mode="error", delta_write_options={'partition_by': ['created_date']})
            else:
                print(f"If no error message, {delta_table_name} delta table created!")
                df_polars_collect_day.write_delta(delta_table_uri, mode=write_mode.lower(), delta_write_options={'partition_by': ['created_date']})
        except Exception as e: 
            return pl.DataFrame()
    elif partition_range == "Month":
        try:
            if write_mode.lower() == "none":
                df_polars_collect_month.write_delta(delta_table_uri, mode="error", delta_write_options={'partition_by': ['created_month']})
                print(f"If no error message, {delta_table_name} delta table created!")
            else:
                df_polars_collect_month.write_delta(delta_table_uri, mode=write_mode.lower(), delta_write_options={'partition_by': ['created_month']})
                print(f"If no error message, {delta_table_name} delta table created!")
        except Exception as e: 
            return pl.DataFrame()
    else:
        print(f"Couldn't make delta table with {partition_range} range")
        return pl.DataFrame()

# Read local delta table Data
def read_delta_table(delta_table_name: str = "", date_range_start: str="", date_range_end: str="", partition_column: str="", version: int = None) -> pl.DataFrame:
    delta_table_path = f"./data/delta_tables/{delta_table_name}"
    if partition_column == "created_date":
        delta_table_pl = pl.scan_delta(delta_table_path, version = version, pyarrow_options={partition_column: [("created_date", ">=", date_range_start.strftime('%Y-%m-%d')),("created_date", "<=", date_range_end.strftime('%Y-%m-%d'))]})
        delta_table_pl = delta_table_pl.collect()
    elif partition_column == "created_month":
        delta_table_pl = pl.scan_delta(delta_table_path, version = version, pyarrow_options={partition_column: [("created_month", ">=", date_range_start.strftime('%Y-%m')),("created_month", "<=", date_range_end.strftime('%Y-%m'))]})
        delta_table_pl = delta_table_pl.collect()
    elif partition_column == "":
        delta_table_pl = pl.scan_delta(delta_table_path, version = version)
        delta_table_pl = delta_table_pl.collect()
    else:
        return pl.DataFrame()
    return delta_table_pl
