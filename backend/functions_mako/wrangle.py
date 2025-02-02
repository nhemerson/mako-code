import datetime
from datetime import datetime
import streamlit as st
import pandas as pd
import functions_mako.utilities as utils

# Convert a dataframe to a csv
def df_to_csv(df) -> pd.DataFrame:
    return df.to_csv(index=False).encode('utf-8')

# Return a list of datetime objects from a string
def datetime_string_to_list(string:  str) -> list:
        if string == "[]":
            datetime_list = None
        else:
            string = string.strip().strip("[]").replace("'","").replace(" ","")
            string = string.split(",")
            datetime_list = [datetime.strptime(date_str, '%Y-%m-%d').date() for date_str in string]
        return datetime_list

# Convert dataframe columns to string
def convert_columns_to_string(data_frame: pd.DataFrame, columns: list) -> pd.DataFrame:
    for column in columns:
        if column in data_frame.columns:
            data_frame[column] = data_frame[column].astype(str)
    return data_frame

# Find first datetime column in dataframe
def find_first_datetime_column(data_frame: pd.DataFrame) -> str:
    column_list = ['order_started_datetime','dispense_time','order_placed_day']
    for column in data_frame.columns:
        if column in column_list:
            return column
    #this runs if the above for loop doesn't return any value
    for column in data_frame.columns:
        if data_frame[column].apply(lambda x: isinstance(x, datetime)).any():
            return column
    return None

def ide_sql_code(code: str) -> str:
    # Standardize the quotes to single quotes
    code = code.replace('"', "'")
    # Replace line breaks with spaces
    code = code.replace('\n', ' ')
    # Get list of available delta tables
    try:
        delta_tables = utils.find_delta_tables()
    except:
        delta_tables = []
    # For each delta table, create a string that is code for reading the delta table
    for table in delta_tables:
        globals = ""
        try:
            for table in delta_tables:
                globals += f"{table} = ingestion.read_delta_table(\"{table}\")\n"
            print(globals)
        except:
            pass

    query = f"""
import streamlit as st
import polars as pl
import functions_mako.ingestion as ingestion
{globals}
dtx = pl.SQLContext(register_globals=True)
output = dtx.execute("{code}", eager=True)
st.dataframe(output)
"""
    try:
        print(query)
        exec(query)
        #output.text(code)
    except Exception as e:
        print(query)
        st.error(f"Error: {e}")
        
