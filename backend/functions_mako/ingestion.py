import polars as pl
import streamlit as st
import json

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
            st.write("Something seems to be wrong:" + str(e))
            print(f"Couldn't make delta table with {partition_by}")
            return pl.DataFrame()
    elif partition_range == "Day":
        try:
            df_polars_collect_day = df_polars_collect.with_columns(pl.col(partition_by).dt.date().alias("created_date"))
            print(f"created_date column created from {partition_by} for {delta_table_name}")
        except Exception as e: 
            st.write("Partition columns must be a date or datetime object:" + str(e))
            print(f"Couldn't make delta table with {partition_by} column")
            return pl.DataFrame()
    elif partition_range == "Month":
        try:
            df_polars_collect_month = df_polars_collect.with_columns(pl.col(partition_by).dt.month().alias("created_month"))
            print(f"created_month column created from {partition_by} for {delta_table_name}")
        except Exception as e: 
            st.write("Partition columns must be a date or datetime object:" + str(e))
            print(f"Couldn't make delta table with {partition_by} column")
            return pl.DataFrame()
    else:
        st.write("Partition range must be either 'daily' or 'monthly'")
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
            st.write("Cannot create delta table: " + str(e))
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
            st.write("Cannot create delta table: " + str(e))
            return pl.DataFrame()
    elif partition_range == "Month":
        try:
            if write_mode.lower() == "none":
                df_polars_collect_month.write_delta(delta_table_uri, mode="error", delta_write_options={'partition_by': ['created_month']})
                st.write(f"If no error message, {delta_table_name} delta table created!")
                print(f"If no error message, {delta_table_name} delta table created!")
            else:
                df_polars_collect_month.write_delta(delta_table_uri, mode=write_mode.lower(), delta_write_options={'partition_by': ['created_month']})
                st.write(f"If no error message, {delta_table_name} delta table created!")
                print(f"If no error message, {delta_table_name} delta table created!")
        except Exception as e: 
            st.write("Cannot create delta table: " + str(e))
            return pl.DataFrame()
    else:
        st.write("Partition range must be either 'daily' or 'monthly'")
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
        st.write("Partition column must be either 'created_date' or 'created_month'")
        return pl.DataFrame()
    return delta_table_pl
