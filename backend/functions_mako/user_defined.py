from datetime import datetime
import polars as pl
import streamlit as st

def custom_function(var_1: str) -> pl.DataFrame:
    """
    A function that returns an empty polars DataFrame with a timestamp.
    var_1: A string input.
    print: var_1 input.
    print: A string output with the current timestamp.
    returns: An empty polars DataFrame.
    """
    print(f"input: {var_1}")
    print(f"data: {datetime.now()}")
    return pl.DataFrame()

def custom_function(var_1: str) -> pl.DataFrame:
    """
    A function that returns an empty polars DataFrame with a timestamp.
    var_1: A string input.
    print: var_1 input.
    print: A string output with the current timestamp.
    returns: An empty polars DataFrame.
    """
    st.write("test")
    print(f"input: {var_1}")
    print(f"data: {datetime.now()}")
    return pl.DataFrame()

