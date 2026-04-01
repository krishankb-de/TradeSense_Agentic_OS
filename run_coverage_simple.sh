#!/bin/bash
# Simple coverage analysis script for TradeSense
# Task 18.11: Verify code coverage

echo "================================================================================"
echo "TRADESENSE CODE COVERAGE ANALYSIS"
echo "Task 18.11: Verify Code Coverage"
echo "================================================================================"

# Python Coverage
echo ""
echo "================================================================================"
echo "PYTHON COVERAGE ANALYSIS"
echo "================================================================================"
echo ""

cd backend

# Run coverage
python -m coverage run -m pytest tests/ -v --tb=short -q
python -m coverage report -m
python -m coverage json -o coverage.json
python -m coverage html -d htmlcov

echo ""
echo "Python coverage report generated:"
echo "  - JSON: backend/coverage.json"
echo "  - HTML: backend/htmlcov/index.html"

cd ..

# TypeScript Coverage
echo ""
echo "================================================================================"
echo "TYPESCRIPT COVERAGE ANALYSIS"
echo "================================================================================"
echo ""

cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

npm run test -- --coverage --run

echo ""
echo "TypeScript coverage report generated:"
echo "  - HTML: frontend/coverage/index.html"

cd ..

echo ""
echo "================================================================================"
echo "COVERAGE ANALYSIS COMPLETE"
echo "================================================================================"
echo ""
echo "View detailed reports:"
echo "  - Python: backend/htmlcov/index.html"
echo "  - TypeScript: frontend/coverage/index.html"
