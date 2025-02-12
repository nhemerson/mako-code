import re
from typing import Tuple, Optional, List
from pathlib import Path

def parse_sql_code(code: str) -> Tuple[str, Optional[str], List[str]]:
    """
    Parse SQL code to extract save directive and dataset names.
    
    Args:
        code: The SQL code including any special comments
        
    Returns:
        Tuple of (sql_query, save_as_name, dataset_names)
    """
    # Extract save directive if present
    save_match = re.search(r'--\s*save_as:\s*(\w+)', code)
    save_as = save_match.group(1) if save_match else None
    
    # Remove the @sql decorator and any special comments
    sql_query = re.sub(r'@sql\s*', '', code)
    sql_query = re.sub(r'--\s*save_as:\s*\w+\s*\n', '', sql_query).strip()
    
    # Extract dataset names from FROM and JOIN clauses
    # This is a simple implementation - might need to be more robust
    dataset_pattern = r'\b(?:FROM|JOIN)\s+(\w+)'
    dataset_names = list(set(re.findall(dataset_pattern, sql_query, re.IGNORECASE)))
    
    return sql_query, save_as, dataset_names

def validate_datasets(dataset_names: List[str], dataset_dir: Path) -> Tuple[bool, List[str]]:
    """
    Validate that all required datasets exist.
    
    Args:
        dataset_names: List of dataset names to validate
        dataset_dir: Path to dataset directory
        
    Returns:
        Tuple of (is_valid, missing_datasets)
    """
    missing_datasets = []
    for name in dataset_names:
        if not (dataset_dir / f"{name}.parquet").exists():
            missing_datasets.append(name)
    
    return len(missing_datasets) == 0, missing_datasets 