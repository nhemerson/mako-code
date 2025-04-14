.PHONY: setup setup-frontend setup-backend run frontend backend build clean

# Check if uv is available
UV_CHECK := $(shell command -v uv 2> /dev/null)

# Set Python environment variables based on UV availability
ifdef UV_CHECK
    VENV_CREATE := cd backend && uv venv
    VENV_PATH := .venv
    PIP_INSTALL := cd backend && . .venv/bin/activate && uv pip install -r requirements.txt
else
    VENV_CREATE := cd backend && python3 -m venv venv
    VENV_PATH := venv
    PIP_INSTALL := cd backend && . venv/bin/activate && pip install -r requirements.txt
endif

# Default target
all: setup

# Setup both frontend and backend
setup: setup-frontend setup-backend

# Setup frontend dependencies
setup-frontend:
	@echo "Setting up frontend dependencies..."
	cd frontend && npm install

# Setup backend dependencies
setup-backend:
ifdef UV_CHECK
	@echo "Setting up backend dependencies using UV..."
else
	@echo "Setting up backend dependencies using pip..."
endif
	@echo "Creating virtual environment..."
	$(VENV_CREATE)
	@echo "Installing dependencies..."
	$(PIP_INSTALL)

# Run both frontend and backend development servers
run:
	@echo "Starting development servers..."
	$(MAKE) backend & $(MAKE) frontend

# Run frontend development server
frontend:
	@echo "Starting frontend server..."
	cd frontend && npm run dev

# Run backend development server
backend:
	@echo "Starting backend server..."
	@echo "API documentation will be available at http://localhost:8001/api/docs"
	cd backend && . $(VENV_PATH)/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8001

# Build frontend for production
build:
	@echo "Building frontend for production..."
	cd frontend && npm run build

# Clean up dependencies and build artifacts
clean:
	@echo "Cleaning up..."
	rm -rf frontend/node_modules
	rm -rf frontend/build
	rm -rf backend/__pycache__
	rm -rf backend/$(VENV_PATH)
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} + 