#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version and ensure Python 3.11 is available
check_python_version() {
    # First check if Python 3.11 is available
    PYTHON_VERSION=${MAKO_PYTHON_VERSION:-3.11}
    if command -v "python${PYTHON_VERSION}" >/dev/null 2>&1; then
        return 0
    fi
    
    # If not, check if uv is installed to potentially install Python 3.11
    if command_exists uv; then
        echo "Python 3.11 not found, but uv is available to create environment"
        return 0
    fi
    
    # If neither condition is met, show error
    echo "Error: Python 3.11 is required and neither python3.11 nor uv was found"
    echo "Please install Python 3.11 or uv (https://astral.sh/uv)"
    exit 1
}

# Function to check Node.js version
check_node_version() {
    if command_exists node; then
        node_version=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$node_version" -lt 16 ]; then
            echo "Error: Node.js 16 or higher is required (found $node_version)"
            exit 1
        fi
    else
        echo "Error: Node.js is not installed"
        exit 1
    fi
}

# Function to start the backend server
start_backend() {
    echo "Starting backend server..."
    cd backend
    
    # Kill any existing uvicorn processes
    echo "Checking for existing backend processes..."
    pkill -f "uvicorn main:app" || true
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo "Creating Python virtual environment..."
        # Remove any existing partial .venv
        rm -rf .venv
        
        # Ensure uv is installed
        if ! command_exists uv; then
            echo "Installing uv..."
            curl -Lf https://astral.sh/uv/install.sh | sh
        fi
        
        # Use uv to create venv with Python 3.11
        echo "Creating venv with Python 3.11..."
        ~/.cargo/bin/uv venv .venv --python=3.11
        
        if [ ! -d ".venv" ]; then
            echo "Error: Failed to create virtual environment"
            exit 1
        fi
    fi
    
    # Activate virtual environment
    if [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate  # Windows
    else
        source .venv/bin/activate      # Unix/MacOS
    fi
    
    # Always check and install requirements
    echo "Checking and updating Python dependencies..."
    rm -f .venv/installed  # Remove the installed marker
    uv pip install --force-reinstall -r requirements.txt >/dev/null 2>&1  # Suppress output
    touch .venv/installed
    
    # Small delay to ensure previous process is fully terminated
    sleep 2
    
    # Now calls the startup.sh and captures its exit status
    ./startup.sh
    BACKEND_STATUS=$?
    
    if [ $BACKEND_STATUS -ne 0 ]; then
        echo "ERROR: Backend server failed to start"
        cd ..
        exit 1
    fi
    
    cd ..
}

# Function to start the frontend server
start_frontend() {
    # Only start frontend if backend started successfully
    if [ $BACKEND_STATUS -eq 0 ]; then
        echo "Starting frontend server..."
        cd frontend
        
        # Install dependencies if needed
        if [ ! -d "node_modules" ]; then
            echo "Installing Node.js dependencies..."
            npm install
        fi
        
        # Start the frontend server
        npm run dev &
        cd ..
    fi
}

# Function to open the browser
open_browser() {
    # Wait for servers to start
    sleep 5
    
    # Open browser based on OS
    case "$(uname -s)" in
        Darwin*)    open http://localhost:5173 ;; # macOS
        Linux*)     xdg-open http://localhost:5173 ;; # Linux
        MINGW*)     start http://localhost:5173 ;; # Windows
    esac
}

# Main script
case "$1" in
    "run")
        # Kill any existing processes first
        echo "Stopping any existing processes..."
        pkill -f "uvicorn main:app" || true
        pkill -f "node.*vite" || true
        sleep 2
        
        # Check requirements
        check_python_version
        check_node_version
        
        # Start servers and track status
        start_backend
        
        # Only continue if backend started successfully
        if [ $BACKEND_STATUS -eq 0 ]; then
            start_frontend
            
            # Open browser
            open_browser
            
            # Show success message only if both servers started
            echo "Mako is running!"
            echo "Frontend: http://localhost:5173"
            echo "Backend: http://localhost:8000"
            echo "Press Ctrl+C to stop all servers"
            
            # Wait for Ctrl+C
            wait
        else
            echo "Mako failed to start due to backend errors"
            exit 1
        fi
        ;;
    "clean")
        echo "Cleaning up Mako environment..."
        rm -rf backend/.venv
        rm -rf frontend/node_modules
        ;;
    "uninstall")
        ./mako clean
        echo "Removing config files..."
        rm -f config/mako.conf
        ;;
    *)
        echo "Usage: ./mako run"
        exit 1
        ;;
esac 