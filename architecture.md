# Mako Architecture Overview

Mako is a modern web-based analytics platform that combines an interactive code editor with data management capabilities. It provides a seamless environment for writing, executing, and analyzing code alongside data visualization features.

## Key Features
- Interactive code editor with syntax highlighting and multiple language support
- Real-time code execution environment
- Data management system for importing and analyzing datasets
- Split-pane interface with adjustable editor and console views
- File management with multiple tabs and file operations
- Dataset visualization and analysis tools

## Frontend Architecture

The frontend is built using SvelteKit and provides a modern, responsive interface with the following components:

### Core Components
- **Code Editor**: Powered by Monaco Editor (same as VS Code), providing:
  - Syntax highlighting
  - Multiple language support (Python, SQL)
  - Tab management for multiple files
  - Keyboard shortcuts (e.g., ⌘ + Enter to run code)

- **Console Output**: Interactive console display for:
  - Code execution results
  - Error messages
  - System output

- **Data Management Interface**:
  - Dataset import functionality
  - Local dataset management
  - Dataset visualization tools
  - File operations (rename, delete, analyze)

### UI Features
- Resizable split-pane layout
- Collapsible sidebar for data management
- Drag-and-drop tab reordering
- File renaming and management
- Dataset preview and analysis tools

### State Management
- File state management for multiple open files
- Dataset state tracking
- UI state management (sidebar collapse, panel sizes)
- Unsaved changes tracking

## Backend Architecture

The backend is built with FastAPI and provides a robust API for code execution and data management:

### Core Services
- **Code Execution Engine**:
  - Secure code execution environment
  - Support for Python code execution
  - Output capture and error handling
  - Safety checks and code validation

- **Data Management System**:
  - Dataset import and processing
  - Parquet file handling
  - Local storage management
  - Dataset operations (read, delete, analyze)

### Security Features
- Code execution sandboxing
- Restricted module imports
- Input validation
- Safe code execution policies

### API Endpoints
- `/execute`: Code execution endpoint
- `/api/upload`: Dataset upload endpoint
- `/api/read-parquet`: Dataset reading endpoint
- `/api/list-datasets`: Dataset listing endpoint
- `/api/delete-dataset`: Dataset deletion endpoint
- `/lint`: Code linting endpoint

### Data Storage
- Local storage for datasets
- Parquet file format support
- File system organization with separate directories for:
  - Local storage
  - Cloud storage (prepared for future implementation)

### Dependencies
- FastAPI for API framework
- Polars for data processing
- Ruff for code linting
- Python standard library for core functionality
