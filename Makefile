# Makefile for EduLens Development
# Provides common development commands for testing, linting, and quality checks

.PHONY: help install install-dev test test-unit test-integration test-performance test-safety test-audio
.PHONY: coverage lint format typecheck security clean build docs serve-docs
.PHONY: pre-commit run-dev db-upgrade db-downgrade db-reset docker-up docker-down

# Default target
.DEFAULT_GOAL := help

# Python interpreter
PYTHON := python3
PIP := $(PYTHON) -m pip

# Project directories
SRC_DIRS := src core orchestrator agents utils database
TEST_DIR := tests
DOCS_DIR := docs

# Coverage threshold
COVERAGE_THRESHOLD := 80

# ============================================================================
# Help
# ============================================================================

help: ## Show this help message
	@echo "EduLens Development Commands"
	@echo "============================"
	@echo ""
	@echo "Installation:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests with coverage"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-performance Run performance tests"
	@echo "  make test-safety      Run safety and content moderation tests"
	@echo "  make test-audio       Run audio processing tests"
	@echo "  make coverage         Run tests with detailed coverage report"
	@echo "  make test-watch       Run tests in watch mode (auto-rerun on changes)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run all linters (ruff, flake8, bandit)"
	@echo "  make format           Format code with black and isort"
	@echo "  make typecheck        Run type checking with mypy"
	@echo "  make security         Run security checks"
	@echo "  make pre-commit       Run all pre-commit checks"
	@echo ""
	@echo "Build & Docs:"
	@echo "  make build            Build distribution packages"
	@echo "  make docs             Generate documentation"
	@echo "  make serve-docs       Serve documentation locally"
	@echo ""
	@echo "Database:"
	@echo "  make db-upgrade       Run database migrations"
	@echo "  make db-downgrade     Rollback last migration"
	@echo "  make db-reset         Reset database to clean state"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up        Start Docker services"
	@echo "  make docker-down      Stop Docker services"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean            Remove build artifacts and cache files"
	@echo "  make run-dev          Run development server"

# ============================================================================
# Installation
# ============================================================================

install: ## Install production dependencies
	@echo "Installing production dependencies..."
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt
	@echo "✓ Production dependencies installed"

install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "✓ Development dependencies installed"

install-all: install install-dev ## Install all dependencies

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests with coverage
	@echo "Running all tests with coverage..."
	pytest $(TEST_DIR) -v \
		--cov \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-fail-under=$(COVERAGE_THRESHOLD)
	@echo "✓ All tests completed"

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	pytest $(TEST_DIR)/unit -v -m unit \
		--cov \
		--cov-report=term-missing
	@echo "✓ Unit tests completed"

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	pytest $(TEST_DIR)/integration -v -m integration \
		--cov \
		--cov-report=term-missing
	@echo "✓ Integration tests completed"

test-performance: ## Run performance tests
	@echo "Running performance tests..."
	pytest $(TEST_DIR)/performance -v -m performance \
		--benchmark-only \
		--benchmark-autosave
	@echo "✓ Performance tests completed"

test-safety: ## Run safety and content moderation tests
	@echo "Running safety tests..."
	pytest $(TEST_DIR)/safety -v -m safety
	@echo "✓ Safety tests completed"

test-audio: ## Run audio processing tests
	@echo "Running audio tests..."
	pytest $(TEST_DIR)/audio -v -m audio
	@echo "✓ Audio tests completed"

test-fast: ## Run fast tests only (skip slow tests)
	@echo "Running fast tests only..."
	pytest $(TEST_DIR) -v -m "not slow" \
		--cov \
		--cov-report=term-missing
	@echo "✓ Fast tests completed"

test-watch: ## Run tests in watch mode (auto-rerun on changes)
	@echo "Starting test watch mode (Ctrl+C to stop)..."
	pytest-watch $(TEST_DIR) -v \
		--cov \
		--cov-report=term-missing

test-parallel: ## Run tests in parallel
	@echo "Running tests in parallel..."
	pytest $(TEST_DIR) -v -n auto \
		--cov \
		--cov-report=term-missing
	@echo "✓ Parallel tests completed"

coverage: ## Generate detailed coverage report
	@echo "Generating coverage report..."
	pytest $(TEST_DIR) -v \
		--cov \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-report=xml \
		--cov-fail-under=$(COVERAGE_THRESHOLD)
	@echo "✓ Coverage report generated"
	@echo "  - Terminal: see above"
	@echo "  - HTML: open htmlcov/index.html"
	@echo "  - XML: coverage.xml"

coverage-html: coverage ## Generate and open HTML coverage report
	@echo "Opening coverage report in browser..."
	@$(PYTHON) -m webbrowser htmlcov/index.html || open htmlcov/index.html || xdg-open htmlcov/index.html

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run all linters
	@echo "Running linters..."
	@echo "→ Running Ruff..."
	ruff check . --output-format=full
	@echo "→ Running Flake8..."
	flake8 $(SRC_DIRS) $(TEST_DIR) --max-line-length=100 --extend-ignore=E203,W503
	@echo "✓ Linting completed"

lint-fix: ## Run linters with auto-fix
	@echo "Running linters with auto-fix..."
	ruff check . --fix
	@echo "✓ Auto-fix completed"

format: ## Format code with black and isort
	@echo "Formatting code..."
	@echo "→ Running Black..."
	black $(SRC_DIRS) $(TEST_DIR)
	@echo "→ Running isort..."
	isort $(SRC_DIRS) $(TEST_DIR)
	@echo "✓ Code formatting completed"

format-check: ## Check code formatting without making changes
	@echo "Checking code formatting..."
	black --check --diff $(SRC_DIRS) $(TEST_DIR)
	isort --check-only --diff $(SRC_DIRS) $(TEST_DIR)
	@echo "✓ Format check completed"

typecheck: ## Run type checking with mypy
	@echo "Running type checks..."
	mypy $(SRC_DIRS) --install-types --non-interactive
	@echo "✓ Type checking completed"

security: ## Run security checks
	@echo "Running security checks..."
	@echo "→ Running Bandit..."
	bandit -r $(SRC_DIRS) -ll
	@echo "→ Checking dependencies with Safety..."
	safety check --json || true
	@echo "→ Checking dependencies with pip-audit..."
	pip-audit --format json || true
	@echo "✓ Security checks completed"

pre-commit: format lint typecheck test-fast ## Run all pre-commit checks
	@echo "✓ All pre-commit checks passed!"

quality: lint typecheck security ## Run all quality checks

# ============================================================================
# Build & Documentation
# ============================================================================

build: clean ## Build distribution packages
	@echo "Building distribution packages..."
	$(PYTHON) -m build
	@echo "✓ Build completed (see dist/ directory)"

build-wheel: ## Build wheel package only
	@echo "Building wheel package..."
	$(PYTHON) -m build --wheel
	@echo "✓ Wheel package built"

docs: ## Generate documentation
	@echo "Generating documentation..."
	cd $(DOCS_DIR) && mkdocs build
	@echo "✓ Documentation generated (see docs/site/)"

serve-docs: ## Serve documentation locally
	@echo "Serving documentation at http://127.0.0.1:8000"
	cd $(DOCS_DIR) && mkdocs serve

docs-deploy: ## Deploy documentation
	@echo "Deploying documentation..."
	cd $(DOCS_DIR) && mkdocs gh-deploy
	@echo "✓ Documentation deployed"

# ============================================================================
# Database
# ============================================================================

db-upgrade: ## Run database migrations
	@echo "Running database migrations..."
	alembic upgrade head
	@echo "✓ Database upgraded"

db-downgrade: ## Rollback last migration
	@echo "Rolling back last migration..."
	alembic downgrade -1
	@echo "✓ Database downgraded"

db-reset: ## Reset database to clean state
	@echo "Resetting database..."
	alembic downgrade base
	alembic upgrade head
	@echo "✓ Database reset"

db-revision: ## Create new migration
	@echo "Creating new migration..."
	@read -p "Enter migration message: " message; \
	alembic revision --autogenerate -m "$$message"
	@echo "✓ Migration created"

db-current: ## Show current migration version
	@echo "Current database version:"
	alembic current

db-history: ## Show migration history
	@echo "Migration history:"
	alembic history --verbose

# ============================================================================
# Docker
# ============================================================================

docker-up: ## Start Docker services
	@echo "Starting Docker services..."
	docker-compose up -d
	@echo "✓ Docker services started"

docker-down: ## Stop Docker services
	@echo "Stopping Docker services..."
	docker-compose down
	@echo "✓ Docker services stopped"

docker-logs: ## Show Docker logs
	docker-compose logs -f

docker-ps: ## Show running Docker containers
	docker-compose ps

docker-rebuild: ## Rebuild and restart Docker services
	@echo "Rebuilding Docker services..."
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "✓ Docker services rebuilt"

# ============================================================================
# Development
# ============================================================================

run-dev: ## Run development server
	@echo "Starting development server..."
	$(PYTHON) cli.py --dev

run-cli: ## Run CLI tool
	@echo "Running CLI..."
	$(PYTHON) cli.py

shell: ## Start Python shell with project context
	@echo "Starting Python shell..."
	$(PYTHON) -i -c "import sys; sys.path.insert(0, '.'); print('EduLens shell ready')"

ipython: ## Start IPython shell
	@echo "Starting IPython shell..."
	ipython

notebook: ## Start Jupyter notebook
	@echo "Starting Jupyter notebook..."
	jupyter notebook

# ============================================================================
# Utilities
# ============================================================================

clean: ## Remove build artifacts and cache files
	@echo "Cleaning build artifacts and cache files..."
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -f .coverage
	rm -f coverage.xml
	rm -f *.log
	@echo "✓ Cleanup completed"

clean-all: clean ## Remove all generated files including virtual environment
	@echo "Removing virtual environment..."
	rm -rf venv/ env/ .venv/
	@echo "✓ Deep cleanup completed"

check-deps: ## Check for outdated dependencies
	@echo "Checking for outdated dependencies..."
	$(PIP) list --outdated

update-deps: ## Update all dependencies
	@echo "Updating dependencies..."
	$(PIP) install --upgrade -r requirements.txt -r requirements-dev.txt
	@echo "✓ Dependencies updated"

freeze: ## Freeze current dependencies
	@echo "Freezing dependencies..."
	$(PIP) freeze > requirements-frozen.txt
	@echo "✓ Dependencies frozen to requirements-frozen.txt"

lock: ## Generate lock file for dependencies
	@echo "Generating dependency lock file..."
	$(PIP) install pip-tools
	pip-compile requirements.txt --output-file requirements-lock.txt
	pip-compile requirements-dev.txt --output-file requirements-dev-lock.txt
	@echo "✓ Lock files generated"

init: install-dev db-upgrade ## Initialize project for development
	@echo "Initializing project..."
	@echo "✓ Project initialized and ready for development"

verify: format-check lint typecheck test ## Verify code quality and tests
	@echo "✓ All verification checks passed!"

ci: verify ## Run CI checks locally
	@echo "✓ CI checks completed successfully!"

# ============================================================================
# Benchmarking and Profiling
# ============================================================================

profile: ## Profile application performance
	@echo "Profiling application..."
	$(PYTHON) -m cProfile -o profile.stats cli.py
	@echo "✓ Profile saved to profile.stats"

profile-view: ## View profiling results
	@echo "Viewing profile results..."
	$(PYTHON) -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"

benchmark: ## Run benchmark tests
	@echo "Running benchmarks..."
	pytest $(TEST_DIR)/performance -v --benchmark-only --benchmark-autosave
	@echo "✓ Benchmarks completed"

# ============================================================================
# Version Management
# ============================================================================

version: ## Show current version
	@echo "Current version:"
	@grep "version" setup.py | head -1 | cut -d'"' -f2

# ============================================================================
# Project Info
# ============================================================================

info: ## Show project information
	@echo "EduLens Project Information"
	@echo "==========================="
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "Pip version: $$($(PIP) --version | cut -d' ' -f2)"
	@echo "Project version: $$(grep 'version' setup.py | head -1 | cut -d'\"' -f2)"
	@echo "Test coverage threshold: $(COVERAGE_THRESHOLD)%"
	@echo ""
	@echo "Key directories:"
	@echo "  Source: $(SRC_DIRS)"
	@echo "  Tests: $(TEST_DIR)"
	@echo "  Docs: $(DOCS_DIR)"
