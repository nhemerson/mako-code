
<img width="207" alt="Screenshot 2025-02-16 at 9 11 12 PM" src="https://github.com/user-attachments/assets/d84dc7f2-95d7-47d0-8c04-bb8701cf396a" />

Analytics Tools for Small Data

## What is Mako Code?

Mako Code is an open source Independent Analytics Environment (IAE) that is built for data people who love to code. It is a workflow designed for fast ad hoc analysis with features to let you productize your work. So you can get to answers quickly while building a foundation for future data products.

Mako Code is not a vibe coding tool, and doesn't come with an LLM. But it does come with an opinion.

- The Monaco Code Editor
- Python built in functions
- Polars only for dataframe manipulation
- Direct link to Polars docs and AI chat
- Bokeh for data viz
- Parquets as the local file type
- Apache Arrow for data serialization
- Pydantic data models
- Ruff for linting
- Fast API backend
- Svelte JS front end

However, it is easy to customize as needed. The goals is to provide a concise workspace that is light in dependencies and easy to install.

## Key Features

- 🚀 Interactive code editor with syntax highlighting and multiple language support
- 📊 Real-time code execution environment
- 💾 Efficient data management system for importing and analyzing datasets
- 🎨 Beautiful split-pane interface with adjustable views
- 📁 Smart file management with multiple tabs
- 📈 Dataset visualization and analysis tools
- ⌨️ Comprehensive keyboard shortcuts for productivity
- 📝 SQL query support with dataset integration
- 📊 Interactive Bokeh plotting functionality

## Code Editor
<img width="2560" alt="Screenshot 2025-03-31 at 10 24 02 am" src="https://github.com/user-attachments/assets/8dd5ce35-309b-4125-b7c6-12c4a2c1cbe1" />

## Dataset Preview
<img width="2560" alt="Screenshot 2025-03-31 at 2 32 44 pm" src="https://github.com/user-attachments/assets/54a985ba-be29-41a1-b197-2c2c45fba1f8" />

## Tech Stack

### Frontend
- SvelteKit
- Monaco Editor (VS Code's editor)
- TypeScript
- Bokeh for interactive visualizations

### Backend
- FastAPI
- Polars for data processing
- Ruff for code linting
- Python standard library

## Local Development Setup

Prerequisites:
- Python 3.11+
- Node.js 20+
- uv package manager (for Python dependencies)

Launch development environment:

To launch Mako have Docker Desktop installed then use Docker Composer

1. Use docker compose
```bash
# build the image
docker-compose build

# run the application
docker-compose up
```

2. Use Make (Alternative Method)
```bash
# Setup both frontend and backend dependencies
make setup

# Run the application (both frontend and backend)
make run

# To run frontend and backend separately:
make frontend  # Runs frontend server
make backend   # Runs backend server

# To clean up dependencies and build artifacts
make clean
```

The backend API documentation will be available at http://localhost:8001/api/docs

## Contributing

We welcome contributions! Please feel free to submit a Pull Request. I will make sure any accepted PRs are added to the next release and you are credited in the changelog.
