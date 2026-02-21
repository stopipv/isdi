.PHONY: help clean build upload upload-test install install-dev test lint format bump-version

# Default Python
PYTHON := python3
PIP := $(PYTHON) -m pip

help:
	@echo "ISDI Scanner - Build and Distribution Commands"
	@echo ""
	@echo "Available targets:"
	@echo "  make install          - Install the package in development mode"
	@echo "  make install-dev      - Install with development dependencies"
	@echo "  make test             - Run tests"
	@echo "  make lint             - Run linter (black format check)"
	@echo "  make format           - Format code with black"
	@echo "  make build            - Build distribution packages"
	@echo "  make upload-test      - Upload to TestPyPI (requires .pypirc)"
	@echo "  make upload           - Upload to PyPI (requires .pypirc)"
	@echo "  make bump-version     - Bump version (PART=patch|minor|major, default=patch)"
	@echo "  make clean            - Remove build artifacts"
	@echo "  make clean-all        - Remove all generated files"
	@echo ""

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m black --check src/ tests/

format:
	$(PYTHON) -m black src/ tests/

build: clean
	$(PYTHON) -m build

upload-test: build
	@echo "Uploading to TestPyPI..."
	$(PYTHON) -m twine upload --repository testpypi dist/*
	@echo ""
	@echo "✓ Successfully uploaded to TestPyPI!"
	@echo "Install with: pip install --index-url https://test.pypi.org/simple/ isdi-scanner"

upload: build
	@echo "Uploading to PyPI..."
	@echo "⚠️  This will publish the package publicly!"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(PYTHON) -m twine upload dist/*; \
		echo ""; \
		echo "✓ Successfully uploaded to PyPI!"; \
		echo "Install with: pip install isdi-scanner"; \
	else \
		echo "Upload cancelled."; \
	fi

VERSION_PART ?= patch

bump-version:
	@$(PYTHON) scripts/bump_version.py

clean:
	rm -rf build/ dist/ *.egg-info .eggs/ src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

clean-all: clean
	rm -rf .venv/ .pytest_cache/ .tox/ htmlcov/ .coverage
	rm -rf .wheel-cache* wheels-*

.DEFAULT_GOAL := help
