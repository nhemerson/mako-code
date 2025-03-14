# Astral UV Commands for Python Virtual Environments

## Basic Virtual Environment Creation

```bash
# Create a virtual environment with the default Python version
uv venv

# Create a virtual environment with a specific name
uv venv .venv

# Create a virtual environment with a specific Python version
uv venv .venv --python=3.10
```

## Installing Packages in the Virtual Environment

```bash
# Install packages from requirements.txt
uv pip install -r requirements.txt

# Install specific packages
uv pip install pandas numpy matplotlib

# Install a specific version of a package
uv pip install django==4.2.0
```

## Managing Python Versions

```bash
# List available Python versions
uv python list

# Create a venv with a specific Python version
uv venv .venv --python=3.9.7
```

## Working with Project Dependencies

```bash
# Create a venv and install dependencies from pyproject.toml
uv venv .venv
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"
```

## Activating the Virtual Environment

```bash
# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

## Additional Useful Commands

```bash
# Upgrade packages in the virtual environment
uv pip install --upgrade package_name

# Generate a requirements.txt file
uv pip freeze > requirements.txt

# Uninstall packages
uv pip uninstall package_name
```
```

This markdown file contains all the useful UV commands organized by category for easy reference.