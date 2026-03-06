# Headless LMS Backend Service (Moodle-Powered)

A production-grade Python backend service that wraps the Moodle REST API, providing a clean, typed interface for LMS operations. Transform Moodle from a monolithic LMS into a headless backend engine.

## Features

- **Complete Moodle API Coverage**: Courses, enrollments, grades, progress, users, and more
- **Type-Safe**: Full Pydantic models for all Moodle data structures
- **Async First**: Built with `httpx` for high-performance async operations
- **Production Ready**: Structured logging, retry logic, comprehensive error handling
- **CLI Tool**: `moodlectl` for administrative tasks and automation
- **Extensible**: Clean service layer design, easy to add FastAPI/Celery layers

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/moodle-backend.git
cd moodle-backend

# Install with pip
pip install -e .

# Or with poetry
poetry install