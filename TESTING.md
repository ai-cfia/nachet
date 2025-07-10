# Testing Documentation

This document provides an overview of testing procedures for the Nachet AI-powered seed identification system.

## Overview

Nachet consists of a React TypeScript frontend and Python Quart backend. Each component has its own comprehensive testing documentation and procedures.

## Component Testing Documentation

### Frontend Testing

For detailed frontend testing procedures, see [frontend/TESTING.md](frontend/TESTING.md).

The frontend testing covers:

- Manual testing procedures for all UI components
- Capture and classification workflows
- Model selection and result display
- Directory management functionality
- Camera/microscope integration testing

### Backend Testing

For detailed backend testing procedures, see [backend/TESTING.md](backend/TESTING.md).

The backend testing covers:

- API endpoint testing
- Database integration testing
- Machine learning pipeline testing
- Storage integration testing

## Quick Start Testing

### Running Frontend Tests

```bash
cd frontend/
npm install
npm run test                    # Run unit tests
npm run test:coverage           # Run tests with coverage
```

### Running Backend Tests

```bash
cd backend/
pip install -r requirements.txt
python -m unittest discover -s tests
```

### Full System Testing

```bash
# Start backend
cd backend && hypercorn -b :8080 app:app

# Start frontend (in another terminal)
cd frontend && npm run dev

# Access application at http://localhost:5173
```

## Test Environment Setup

Ensure you have the following configured:

- PostgreSQL database connection
- Azure Storage connection string
- ML model endpoints (for integration testing)
- Required environment variables (see `.env.template`)

For detailed setup instructions, see the main [README.md](README.md) file.
