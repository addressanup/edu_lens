#!/bin/bash
# EduLens Test Runner Script
# Usage: ./scripts/run_tests.sh [unit|integration|performance|safety|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_status() {
    echo -e "${GREEN}[EduLens]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[Warning]${NC} $1"
}

echo_error() {
    echo -e "${RED}[Error]${NC} $1"
}

run_unit_tests() {
    echo_status "Running unit tests..."
    pytest tests/unit -v --tb=short --cov=src --cov-report=term-missing
}

run_integration_tests() {
    echo_status "Running integration tests..."
    pytest tests/integration -v --tb=short
}

run_performance_tests() {
    echo_status "Running performance tests..."
    pytest tests/performance -v --tb=short --benchmark-only
}

run_safety_tests() {
    echo_status "Running safety tests..."
    pytest tests/safety -v --tb=short
}

run_all_tests() {
    echo_status "Running all tests..."
    pytest tests/ -v --tb=short --cov=src --cov-report=html
    echo_status "Coverage report generated in htmlcov/"
}

# Main
case "${1:-all}" in
    unit)
        run_unit_tests
        ;;
    integration)
        run_integration_tests
        ;;
    performance)
        run_performance_tests
        ;;
    safety)
        run_safety_tests
        ;;
    all)
        run_all_tests
        ;;
    *)
        echo "Usage: $0 [unit|integration|performance|safety|all]"
        exit 1
        ;;
esac

echo_status "Tests completed!"
