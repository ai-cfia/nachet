#!/bin/bash

# Datastore Test Runner Script
# This script runs the complete test cycle: cleanup -> setup -> tests -> cleanup

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

# Check if we're in the datastore directory
if [ ! -f "pyproject.toml" ] || [ ! -d "tests" ]; then
    print_error "This script must be run from the datastore directory"
    exit 1
fi

# Check if .env.test exists
if [ ! -f ".env.test" ]; then
    print_error ".env.test file not found. Please ensure test environment is configured."
    exit 1
fi

print_status "Starting datastore test cycle..."

# Step 1: Load environment variables
print_status "Loading test environment variables..."
set -a
source .env.test.local
set +a
print_success "Environment variables loaded"

# Step 2: Initial cleanup
print_status "Step 1/4: Running initial test cleanup..."
if uv run python tests/test_cleanup.py <<< "y"; then
    print_success "Initial cleanup completed"
else
    print_warning "Initial cleanup failed or was already clean"
fi

# Step 3: Test setup
print_status "Step 2/4: Setting up test database..."
if uv run python tests/test_setup.py; then
    print_success "Test database setup completed"
else
    print_error "Test database setup failed"
    exit 1
fi

# Step 4: Run all tests
print_status "Step 3/4: Running all tests..."
echo "----------------------------------------"

# Run tests with verbose output and collect results
if uv run python -m pytest tests/ -v --tb=short; then
    print_success "All tests passed!"
    TEST_RESULT=0
else
    print_error "Some tests failed"
    TEST_RESULT=1
fi

echo "----------------------------------------"

# Step 5: Final cleanup
print_status "Step 4/4: Running final test cleanup..."
if uv run python tests/test_cleanup.py <<< "y"; then
    print_success "Final cleanup completed"
else
    print_warning "Final cleanup had issues"
fi

# Summary
echo ""
print_status "Test cycle completed!"
if [ $TEST_RESULT -eq 0 ]; then
    print_success "All tests passed successfully! 🎉"
else
    print_error "Some tests failed. Check the output above for details."
fi

exit $TEST_RESULT
