#!/bin/bash
# The Vitality Vanguard - Quick Start Script
# This script helps you set up and run your first meta-analysis

set -e  # Exit on error

echo "=================================="
echo "The Vitality Vanguard - Quick Start"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
    echo "❌ Python 3.8+ required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION"
echo ""

# Check if dependencies are installed
echo "Checking dependencies..."
if ! python3 -c "import sklearn" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    echo "Installing scispacy model..."
    pip3 install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_lg-0.5.1.tar.gz
else
    echo "✓ Dependencies already installed"
fi
echo ""

# Check .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found"
    echo "Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "❗ IMPORTANT: Edit .env and add your API keys:"
    echo "   - OPENAI_API_KEY (required for data extraction)"
    echo "   - PUBMED_API_KEY (optional, increases rate limits)"
    echo ""
    echo "Press Enter after you've edited .env, or Ctrl+C to exit and edit later"
    read -r
fi

# Check if API key is configured
if grep -q "your_api_key_here" .env 2>/dev/null; then
    echo "⚠️  Warning: .env file still contains placeholder API key"
    echo "Some modules may not work without a valid API key"
    echo ""
fi

# Run example
echo "=================================="
echo "Running Example Meta-Analysis"
echo "=================================="
echo ""
echo "Research Question: Does resveratrol improve glycemic control in type 2 diabetes?"
echo ""

# Run with existing protocol
python3 pipeline.py \
  --protocol protocol.json \
  --output results_demo/ \
  --max-results 100

echo ""
echo "=================================="
echo "✓ Demo Complete!"
echo "=================================="
echo ""
echo "Results saved to: results_demo/"
echo ""
echo "Next steps:"
echo "  1. View PRISMA diagram: open results_demo/3_screening/prisma_flow.png"
echo "  2. Check forest plots: ls results_demo/5_analysis/forest_*.png"
echo "  3. Read final report: cat results_demo/FINAL_REPORT.md"
echo ""
echo "To run your own meta-analysis:"
echo "  python3 pipeline.py --question \"Your research question here\""
echo ""
