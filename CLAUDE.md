# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a receipt scanner API that extracts information from receipt images using OCR (Tesseract) and OpenAI's GPT models. The system analyzes receipt images to extract store name, total amount, purchase date, and expense category.

## Architecture

### Core Components

- **API Layer** (`api/main.py`): FastAPI application with single endpoint `/receipt-analyze`
- **Receipt Scanning** (`src/receipt_scanner_model/scan_receipt.py`): OCR processing using Tesseract with image preprocessing
- **AI Analysis** (`src/receipt_scanner_model/analyze.py`): OpenAI GPT integration for extracting structured data
- **S3 Integration** (`src/receipt_scanner_model/s3_client.py`): AWS S3 client for image download
- **Settings** (`src/receipt_scanner_model/setting.py`): Environment variable management using pydantic-settings

### Data Flow

1. API receives filename in request
2. S3Client downloads image bytes from AWS S3 using filename
3. OCR processing extracts text from image (Tesseract + image preprocessing)
4. OpenAI GPT analyzes OCR text to extract structured receipt data
5. Returns ReceiptDetail with store_name, amount, date, category

### Project Structure

- `src/receipt_scanner_model/`: Main application code
- `api/`: FastAPI application entry point
- `investigation/`: Research code for OCR techniques (not used in production)
- `tests/`: Test files organized by component (test_api/, test_src/)
- `raw/`: Sample receipt images for testing
- `output/`: OCR processing results and debug output

## Development Commands

### Environment Setup

```bash
# Install dependencies and setup virtual environment
rye sync

# Setup pre-commit hooks
rye run pre-commit install
```

### Running the Application

```bash
# Local development server
uvicorn api.main:app --reload

# Docker build and run
docker build . -t receipt-scanner-model --build-arg PYTHON_VERSION="$(cat .python-version)"
docker run -p 127.0.0.1:8000:8000 -e OPENAI_API_KEY receipt-scanner-model
```

### Testing

```bash
# Run all tests
pytest tests

# Run specific test directories
pytest tests/test_api      # API tests
pytest tests/test_src      # Source code tests

# Run single test file
pytest tests/test_api/test_main.py

# Run with coverage (c1 coverage measurement)
coverage run --branch -m pytest tests
coverage report --show-missing --include="api/*,src/*"
```

### Code Quality

```bash
# Lint and format code (via pre-commit)
rye run pre-commit run --all-files

# Manual linting
rye run ruff check
rye run ruff format

# Type checking
rye run pyright
```

### Dependencies

```bash
# Add new dependency
rye add "package>=version"

# Remove dependency
rye remove package

# Sync after changes
rye sync
```

## Environment Variables

Required environment variables (managed via .env file):

- `OPENAI_API_KEY`: OpenAI API key for GPT analysis
- `AWS_ACCESS_KEY_ID`: AWS access key for S3
- `AWS_SECRET_ACCESS_KEY`: AWS secret key for S3
- `AWS_DEFAULT_REGION`: AWS region for S3
- `BUCKET_NAME`: S3 bucket name (defaults to "receipt-scanner-v1")

## External Dependencies

- **Tesseract OCR**: Must be installed system-wide (`brew install tesseract` on macOS)
- **AWS S3**: For image storage and retrieval
- **OpenAI API**: For intelligent text analysis and data extraction

## Error Handling

The API implements comprehensive error handling for S3 operations:

- 400: Bad Request / Not Found (user error)
- 503: Service Unavailable (temporary S3 issues)
- 500: Internal Server Error (permissions/server issues)
