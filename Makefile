.PHONY: setup setup-frontend setup-backend dev frontend backend build clean

# Check if uv is available
UV_CHECK := $(shell command -v uv 2> /dev/null)

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
	@echo "Setting up backend dependencies using uv..."
	@echo "Creating virtual environment..."
	cd backend && uv venv
	@echo "Installing dependencies..."
	cd backend && uv pip install -r requirements.txt
else
	@echo "Setting up backend dependencies using pip..."
	@echo "Creating virtual environment..."
	cd backend && python3 -m venv venv
	@echo "Installing dependencies..."
	cd backend && . venv/bin/activate && python3 -m pip install -r requirements.txt
endif

# Run both frontend and backend development servers
dev:
	@echo "Starting development servers..."
	$(MAKE) backend & $(MAKE) frontend

# Run frontend development server
frontend:
	@echo "Starting frontend server..."
	cd frontend && npm run dev

# Run backend development server
backend:
ifdef UV_CHECK
	@echo "Starting backend server with UV environment..."
	cd backend && . .venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000
else
	@echo "Starting backend server with pip environment..."
	cd backend && . venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000
endif

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
	rm -rf backend/venv
	rm -rf backend/.venv
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Initialize data directories
init-data:
	@echo "Creating data directories..."
	mkdir -p data/local_storage
	mkdir -p data/cloud_storage
	mkdir -p functions

# Run tests
test:
	@echo "Running tests..."
ifdef UV_CHECK
	cd backend && . .venv/bin/activate && python -m pytest
else
	cd backend && . venv/bin/activate && python -m pytest
endif

# Install development dependencies
dev-setup:
ifdef UV_CHECK
	@echo "Installing development dependencies using uv..."
	cd backend && . .venv/bin/activate && uv pip install -r requirements-dev.txt
else
	@echo "Installing development dependencies using pip..."
	cd backend && . venv/bin/activate && pip install -r requirements-dev.txt
endif