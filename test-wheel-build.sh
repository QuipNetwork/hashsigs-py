#!/bin/bash
# Test wheel building locally using the same manylinux container as cibuildwheel

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Testing wheel build locally with manylinux2014_x86_64${NC}"

# Clean up any existing containers
docker rm -f hashsigs-wheel-test 2>/dev/null || true

# Run the same container that cibuildwheel uses
echo -e "${YELLOW}Starting manylinux2014_x86_64 container...${NC}"
docker run -it --name hashsigs-wheel-test \
  -v "$(pwd):/project" \
  -w /project \
  quay.io/pypa/manylinux2014_x86_64:2024-01-23-12ffabc \
  bash -c '
set -euo pipefail

echo "=== Installing Rust toolchain ==="
curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source ~/.cargo/env
rustc --version
cargo --version

echo "=== Setting up Python 3.11 ==="
export PATH="/opt/python/cp311-cp311/bin:$PATH"
python --version
pip --version

echo "=== Installing build dependencies ==="
pip install --upgrade pip
pip install build setuptools-rust

echo "=== Cleaning any existing build artifacts ==="
rm -rf build/ dist/ *.egg-info/ hashsigs/_rust*.so hashsigs/__pycache__/
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "=== Building wheel ==="
export HASHSIGS_BUILD_RUST=1
python -m build --wheel --outdir /tmp/wheels

echo "=== Checking built wheel ==="
ls -la /tmp/wheels/
WHEEL=$(ls /tmp/wheels/*.whl)
echo "Built wheel: $WHEEL"

echo "=== Inspecting wheel contents ==="
python -m zipfile -l "$WHEEL" | grep -E "(\.so|\.pyd)" || echo "No native extensions found"

echo "=== Running auditwheel show ==="
auditwheel show "$WHEEL"

echo "=== Attempting auditwheel repair ==="
mkdir -p /tmp/repaired
auditwheel repair --strip -w /tmp/repaired "$WHEEL" || {
  echo "auditwheel repair failed, trying without --strip"
  auditwheel repair -w /tmp/repaired "$WHEEL" || {
    echo "auditwheel repair failed completely, copying wheel as-is"
    cp "$WHEEL" /tmp/repaired/
  }
}

echo "=== Final wheels ==="
ls -la /tmp/repaired/

echo "=== Testing wheel installation and import ==="
pip install /tmp/repaired/*.whl
python -c "import hashsigs; print(\"Package imported successfully\")"
python -c "import hashsigs._rust as m; print(\"Rust extension ok:\", m)"

echo "=== Copying wheels back to host ==="
cp /tmp/repaired/*.whl /project/dist/ 2>/dev/null || mkdir -p /project/dist && cp /tmp/repaired/*.whl /project/dist/

echo "=== SUCCESS: Wheel built and tested ==="
'

# Clean up
docker rm hashsigs-wheel-test

echo -e "${GREEN}Local wheel test completed! Check ./dist/ for the built wheel.${NC}"
