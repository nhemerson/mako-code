import streamlit as st
import polars as pl
import os
import functions_mako.ingestion as ingestion
import functions_mako.utilities as utils



def local_file_to_delta_table(file_path: str="", delta_table_name: str="", partition_by: str="", partition_range: str="", save_mode: str="") -> pl.DataFrame:
    if file_path:
        print(file_path)
        if os.path.isfile(file_path):
            try:
                dataframe = utils.load_file(file_path)
                print(f"{delta_table_name} dataframe read")
                
                # Check if the dataframe is not empty
                if dataframe is not None:
                    st.write(f"{delta_table_name} Successfully Loaded")
                    ingestion.create_delta_table(dataframe, delta_table_name, partition_by, partition_range, save_mode)
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                return None
        else:
            st.error("That data set does not appear to exist")