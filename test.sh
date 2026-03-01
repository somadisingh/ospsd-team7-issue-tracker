#!/usr/bin/env bash
# Testing utility script for the project

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Help function
show_help() {
    cat << EOF
Testing utility for ospsd-team-07

Usage: ./test.sh [COMMAND] [OPTIONS]

Commands:
    all                 Run all tests with coverage (default)
    unit                Run only unit tests
    integration         Run only integration tests
    e2e                 Run only e2e tests
    coverage            Generate HTML coverage report
    collect             Collect and list all tests
    watch               Run tests in watch mode (requires pytest-watch)
    clean               Clean up test artifacts
    help                Show this help message

Options:
    -v, --verbose       Verbose output
    -s, --show-print    Show print statements
    -x, --exit-first    Stop on first failure
    --no-cov            Skip coverage reporting
    
Examples:
    ./test.sh unit -v
    ./test.sh integration --no-cov
    ./test.sh e2e -v
    ./test.sh coverage
EOF
}

# Colors for output
echo_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

echo_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

# Check if pytest is installed
check_pytest() {
    if ! python -m pytest --version &> /dev/null; then
        echo_warning "pytest not found. Installing dependencies..."
        pip install -e . -q
        pip install -e "components/issue_tracker_client_api[dev]" -q
        pip install -e "components/trello_client_impl[dev]" -q
        echo_success "Dependencies installed"
    fi
}

# Run all tests
run_all_tests() {
    check_pytest
    echo_info "Running all tests with coverage..."
    python -m pytest "$@"
}

# Run unit tests
run_unit_tests() {
    check_pytest
    echo_info "Running unit tests..."
    python -m pytest -m unit "$@"
}

# Run integration tests
run_integration_tests() {
    check_pytest
    echo_info "Running integration tests..."
    python -m pytest -m integration "$@"
}

# Run e2e tests
run_e2e_tests() {
    check_pytest
    if [[ -z "$TRELLO_API_KEY" ]] || [[ -z "$TRELLO_TOKEN" ]] || [[ -z "$TRELLO_BOARD_ID" ]]; then
        echo_warning "Trello credentials not set. E2E tests will be skipped."
        echo_info "To enable E2E tests, set: TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID"
    fi
    echo_info "Running e2e tests..."
    python -m pytest -m e2e "$@"
}

# Generate coverage report
generate_coverage() {
    check_pytest
    echo_info "Generating coverage report..."
    python -m pytest --cov=components --cov-report=term-missing --cov-report=html "$@"
    echo_success "Coverage report generated in htmlcov/index.html"
    
    # Try to open in browser
    if command -v open &> /dev/null; then
        open htmlcov/index.html
    elif command -v xdg-open &> /dev/null; then
        xdg-open htmlcov/index.html
    fi
}

# Collect tests
collect_tests() {
    check_pytest
    echo_info "Collecting tests..."
    python -m pytest --collect-only -q
}

# Watch mode
watch_tests() {
    check_pytest
    if ! python -m ptw --version &> /dev/null 2>&1; then
        echo_warning "pytest-watch not installed. Installing..."
        pip install pytest-watch -q
    fi
    echo_info "Running tests in watch mode (Ctrl+C to exit)..."
    python -m ptw "$@"
}

# Clean artifacts
clean_artifacts() {
    echo_info "Cleaning test artifacts..."
    rm -rf .pytest_cache
    rm -rf htmlcov
    rm -rf .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo_success "Cleaned test artifacts"
}

# Parse arguments
COMMAND="${1:-all}"
shift || true

case "$COMMAND" in
    unit)
        run_unit_tests "$@"
        ;;
    integration)
        run_integration_tests "$@"
        ;;
    e2e)
        run_e2e_tests "$@"
        ;;
    coverage)
        generate_coverage "$@"
        ;;
    collect)
        collect_tests "$@"
        ;;
    watch)
        watch_tests "$@"
        ;;
    clean)
        clean_artifacts
        ;;
    help|--help|-h)
        show_help
        ;;
    all)
        run_all_tests "$@"
        ;;
    *)
        echo_warning "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac

echo_success "Done!"
