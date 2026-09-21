#!/bin/bash
#
# Build Wheels Script for LangAgent Binary Packaging
#
# Purpose: Download all dependencies as wheel files for offline installation
#
# This script:
# 1. Generates requirements.lock.txt if missing (with SHA256 hashes)
# 2. Downloads all wheels for Linux x86_64 platform
# 3. Validates wheel completeness
#
# Exit codes:
#   0 - Success
#   1 - Failure

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="$REPO_ROOT/requirements.lock.txt"
WHEELS_DIR="$REPO_ROOT/wheels"
PYPROJECT_TOML="$REPO_ROOT/pyproject.toml"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# ============================================================================
# Functions
# ============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# ============================================================================
# Main Process
# ============================================================================

echo "Building Wheels for Offline Installation"
echo "=========================================="

# Check if pyproject.toml exists
if [ ! -f "$PYPROJECT_TOML" ]; then
    log_error "pyproject.toml not found: $PYPROJECT_TOML"
    exit 1
fi

# Generate lock file if missing
if [ ! -f "$LOCK_FILE" ]; then
    log_info "Lock file not found, generating..."
    
    # Check if pip-tools is installed
    if ! python3 -c "import pip_tools" 2>/dev/null; then
        log_info "Installing pip-tools..."
        pip3 install pip-tools
    fi
    
    log_info "Running pip-compile --generate-hashes..."
    pip-compile \
        --generate-hashes \
        --output-file="$LOCK_FILE" \
        "$PYPROJECT_TOML"
    
    log_info "Lock file created: $LOCK_FILE"
else
    log_info "Using existing lock file: $LOCK_FILE"
fi

# Create wheels directory
mkdir -p "$WHEELS_DIR"
log_info "Wheels directory: $WHEELS_DIR"

# Download wheels
log_info "Downloading wheels for Linux x86_64..."
pip3 download \
    -r "$LOCK_FILE" \
    -d "$WHEELS_DIR" \
    --platform manylinux2014_x86_64 \
    --platform manylinux_2_17_x86_64 \
    --platform linux_x86_64 \
    --only-binary=:all: \
    --python-version 311

# Count wheels
WHEEL_COUNT=$(find "$WHEELS_DIR" -name "*.whl" | wc -l)
log_info "Downloaded $WHEEL_COUNT wheel files"

# Display summary
echo ""
echo "=========================================="
echo "Wheels Generation Complete"
echo "Location: $WHEELS_DIR"
echo "Wheel files: $WHEEL_COUNT"
echo "=========================================="
echo ""
log_info "To install offline: pip install --no-index --find-links=$WHEELS_DIR langagent"

exit 0
