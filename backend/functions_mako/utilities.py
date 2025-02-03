
import polars as pl
import json
import os
import subprocess
import tempfile
from typing import Generator

##### Global Utiliies #####

# Make general env variable for keys.json
def env_keys(keys_path: str) -> dict:
    storage_options = {"google_service_account": keys_path }
    return storage_options

# Combine and deduplicate library imports and code for custom functions
def combine_and_deduplicate_funcs(libs_data: dict, funcs_data: dict) -> str:
    """
    Combine and deduplicate library imports and code for custom functions.

    Args:
        libs_data (dict): The dictionary containing library names as keys and library code as values.
        funcs_data (dict): The dictionary containing function names as keys and function code as values.

    Returns:
        str: The combined and deduplicated library imports and function code.
    """
    # Use a set to store unique library imports
    unique_libs = set()
    for lib in libs_data.values():
        # Split the libraries by newline and add each one to the set
        for line in lib.split('\n'):
            if line.strip():  # Avoid adding empty lines
                unique_libs.add(line.strip())
                print(unique_libs)
    
    # Combine the unique library imports into a single string
    combined_code = "\n".join(sorted(unique_libs)) + "\n\n"
    
    # Add the function code
    for func_code in funcs_data.values():
        combined_code += func_code
    
    print(combined_code)
    return combined_code


# Check python syntax of a custom function using compile
def check_python_syntax(func_code: str, type: str) -> bool:
    """
    Check the syntax of a Python function.

    Args:
        func_code (str): The Python function code to check.
        type (str): The type of syntax check to perform. Can be "compile" or "pylint".

    Returns:
        bool: True if the syntax is correct, False otherwise.
    """
    if type == "compile":
        try:
            compile(func_code, "string", "exec")
            return True
        except SyntaxError:
            return False
        
    elif type == "pylint":
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(func_code)
            file_path = temp_file.name
        try:
            result = subprocess.run(["pylint", file_path], capture_output=True)
            if result.returncode == 0:
                return True
            else:
                return result.stdout.decode()  # Return the pylint output as a string
        finally:
            os.unlink(file_path)

    elif type == "ruff":
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(func_code)
            file_path = temp_file.name
        try:
            result = subprocess.run(["ruff", "check", file_path], capture_output=True)
            if result.returncode == 0:
                return True
            else:
                return result.stdout.decode()  # Return the pylint output as a string
        finally:
            os.unlink(file_path)
        
            
    else:
        raise ValueError("Invalid type. Must be either 'compile' or 'pylint'.")
    


# Add new function to a JSON file
def new_cust_func_json(func_name: str, func_code: str) -> None:
    """
    Updates the delta table paths JSON file with a new key-value pair.

    Args:
        new_key (str): New function name.
        new_value (str): The fuction code for the new name.

    Returns:
        None
    """
    file_path = os.path.join("./lookups/dynamic/","user_functions.json")

    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            print("JSON file read successfully!")
    except FileNotFoundError:    
        data = {}
        print("File not found")

    
    data[func_name] = func_code + '\n'

    print(data)
    
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
            print("Function added to json successfully!")
    except Exception as e:
        print(e)

# Write new libary for custom functions to a JSON file
def new_cust_lib_json(lib_name: str, lib_code: str) -> None:
    """
    Updates the delta table paths JSON file with a new key-value pair.

    Args:
        new_key (str): New library name.
        new_value (str): The library code for the new name.

    Returns:
        None
    """
    file_path = os.path.join("./lookups/dynamic/","user_libraries.json")

    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}

    
    data[lib_name] = lib_code + '\n'

    print(lib_code)
    
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
            print("Library added to json successfully!")
    except Exception as e:  
        print(e)

# Write custom function to a file
def write_cust_func_to_file() -> None:
    # File Paths
    file_path_func = os.path.join("./lookups/dynamic/","user_functions.json")
    file_path_libs = os.path.join("./lookups/dynamic/","user_libraries.json")

    # Read the JSON files
    libs_data = read_json_file(file_path_libs)
    print(libs_data)
    funcs_data = read_json_file(file_path_func)

    # Combine and deduplicate library imports
    combined_libs = combine_and_deduplicate_funcs(libs_data, funcs_data)    
    print(combined_libs)

    filename = "./functions/user_defined.py"

    try:
        with open(filename, 'w') as file: 
                file.write(combined_libs)
                print("Function written to file successfully!")
    except FileNotFoundError:   
        combined_libs = ""
        print("File not found")

# Create a new code snippet to a JSON file
def new_code_snippet_json(type: str, name: str, code: str) -> None:
    """
    Updates the code_snippets JSON file with a new key-value pair.

    Args:
        name (str): New name for snippet to be added to the JSON file.
        code (str): The code for the new snippet.

    Returns:
        None
    """
    if type == "python":
        try:
            file_path = os.path.join("./lookups/dynamic/","py_code_snippets.json")
            print(file_path)

            if not os.path.exists(file_path):
                with open(file_path, "w") as file:
                    file.write("{\n\n}")
                    print(f"Created file {file_path}")

            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
            except FileNotFoundError:
                data = {}

            data[name] = code + '\n'

            print(code)

            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)
                print("Python code snippet added to json successfully!")

        except Exception as e:
            print(e)
        

    elif type == "sql":
        try:
            file_path = os.path.join("./lookups/dynamic/","sql_code_snippets.json")

            if not os.path.exists(file_path):
                with open(file_path, "w") as file:
                    file.write("{\n\n}")
                    print(f"Created file {file_path}")

            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
            except FileNotFoundError:
                data = {}

            data[name] = code

            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)

            print("SQL code snippet added to json successfully!")

        except Exception as e:
            print(e)
    

# Delete a function from the JSON file
def delete_dt_path_json(key_to_delete: str) -> None:
    """
    Delete a key-value pair from a JSON file.

    Args:
        key_to_delete (str): The key to be deleted from the JSON file.

    Returns:
        None
    """
    file_path = os.path.join("./lookups/dynamic/","delta_table_paths.json")
    
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    if key_to_delete in data:
        del data[key_to_delete]
    
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Load a file from the specified file path
def load_file(file_path: str="") -> pl.DataFrame:
    """
    Load a file from the specified file path.

    Args:
        file_path (str): The path to the file.

    Returns:
        pl.Dataframe: The loaded file as a Polars DataFrame if successful, an empty dataframe otherwise.
    """
    # Check the file extension and load the file accordingly
    if file_path.endswith(".csv"):
        print("CSV file read")
        df = pl.read_csv(file_path)
        df = df.with_columns(pl.all().name.to_lowercase())
        print(df.columns)
        df = df.rename(lambda name: name.replace(".", "_").replace(" ", "_"))
        return df
    elif file_path.endswith(".parquet"):
        print("Parquet file read")
        df = pl.read_parquet(file_path)
        df = df.with_columns(pl.all().name.to_lowercase())
        df = df.rename(lambda name: name.replace(".", "_").replace(" ", "_"))
        return df
    elif file_path.endswith(".json"):
        print("JSON file read")
        df = pl.read_json(file_path)
        df = df.with_columns(pl.all().name.to_lowercase())
        df = df.rename(lambda name: name.replace(".", "_").replace(" ", "_"))
        return df
    else:
        print("The file must be CSV, Parquet or JSON.")
        pl.DataFrame()

# Get list of local datasets in the dataset folder
def find_local_datasets() -> list[str]:
    """
    Get the names of all files within the specified base_path.
    """
    base_path = "./data/datasets/"
    # List all entries in the base path
    all_entries = os.listdir(base_path)
    # Filter out directories from all entries
    files = [entry for entry in all_entries if os.path.isfile(os.path.join(base_path, entry))]
    return files

# Get list of delta tables locally
def find_delta_tables() -> list[str]:
    """
    Get the names of all directories within the specified base_path.
    """
    base_path = "./data/delta_tables/"
    # List all entries in the base path
    all_entries = os.listdir(base_path)
    # Filter out directories from all entries
    directories = [entry for entry in all_entries if os.path.isdir(os.path.join(base_path, entry))]
    return directories

# Find first delta log for a delta lake

def find_first_log_file(delta_table_name: str = "") -> str:
    """
    Find the latest log file in the Delta Lake log directory.

    Args:
        delta_table_name (str): The name of the Delta table. Defaults to an empty string.

    Returns:
        str: The path of the latest log file in the Delta Lake log directory.
    """
    base_path = f"./data/delta_tables/{delta_table_name}/_delta_log/"
    log_files = [f for f in os.listdir(base_path) if f.endswith('.json')]
    latest_log_file = min(log_files, key=lambda x: int(x.split('.')[0]))
    return os.path.join(base_path, latest_log_file)

# Find latest delta log for a delta lake
def find_latest_log_file(delta_table_name: str = "") -> str:
    """
    Find the latest log file in the Delta Lake log directory.

    Args:
        delta_table_name (str): The name of the Delta table. Defaults to an empty string.

    Returns:
        str: The path of the latest log file in the Delta Lake log directory.
    """
    base_path = f"./data/delta_tables/{delta_table_name}/_delta_log/"
    log_files = [f for f in os.listdir(f"./data/delta_tables/{delta_table_name}/_delta_log/") if f.endswith('.json')]
    latest_log_file = max(log_files, key=lambda x: int(x.split('.')[0]))
    return os.path.join(base_path, latest_log_file)

# Read any JSON file
def read_json_file(log_file: str="") -> dict:
    """
    Read JSON data from a file.

    Args:
        log_file (str): The path to the JSON log file. Defaults to an empty string.

    Returns:
        dict: The JSON data as a dictionary.
    """
    with open(log_file, 'r') as file:
        return json.load(file)

def parse_multiline_json(log_file: str="") -> Generator[dict, None, None]:
    """
    Parse a JSON log file with multiple lines.

    Args:
        log_file (str): The path to the JSON log file. Defaults to an empty string.

    Yields:
        dict: The parsed JSON data as a dictionary for each line in the log file.
    """
    with open(log_file, 'r') as f:
        for line in f:
            yield json.loads(line)

def extract_stats_from_log(log_data: dict) -> list[dict]:
    """
    Extract the 'stats' section from the log data.

    Args:
        log_data (dict): The log data as a dictionary.

    Returns:
        list[dict]: The extracted 'stats' section from the log data.
    """
    # Assuming 'stats' is located in the entries of the log data
    stats = []
    for entry in log_data:
        if 'stats' in entry:
            stats.append(entry['stats'])
    return stats


#####################

# Get Report Names
def get_report_names() -> str:
    try:
        with open('./data/report_names/report_names_list.json', 'r') as file:
            data = json.load(file)
            return data["report_names"]
    except FileNotFoundError:
        return "No report names found"


