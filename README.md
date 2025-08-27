# hashsigs (Python)

Python package for WOTS+ with optional Rust acceleration from hashsigs-rs.

## Installation

```bash
pip install hashsigs
```

For best performance, ensure you have Rust installed (the package will automatically build the Rust extension if available):

```bash
# Install Rust toolchain (optional, for better performance)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
# Then install hashsigs
pip install hashsigs
```

## Quick Usage

```python
import hashsigs

# Create a WOTS+ instance
wots = hashsigs.WOTSPlus()

# Generate a key pair
private_key, public_key = wots.generate_key_pair()

# Sign a message
message = b"Hello, world!"
signature = wots.sign(private_key, message)

# Verify the signature
is_valid = wots.verify(public_key, message, signature)
print(f"Signature valid: {is_valid}")  # True

# Check if Rust acceleration is available
try:
    import hashsigs._rust
    print("Using Rust acceleration")
except ImportError:
    print("Using pure Python implementation")
```

## Development Setup

For contributors and advanced users who want to build from source:

```bash
# from the repo root
python3 -m venv .hashsigs
source .hashsigs/bin/activate
python -m pip install -U pip pytest pytest-cov

# Ensure Rust toolchain (required to build the optional extension)
# macOS: also ensure Xcode CLT: xcode-select --install
rustup --version || brew install rust
cargo --version

# Install dev deps and try to build rust extension (quote extras in zsh)
pip install -v -e '.[rust,dev]'
# Install keccak provider (required for vectors when falling back to Python)
pip install pycryptodome
# or: pip install pysha3

# Quick check the extension is present (optional)
python -c "import hashsigs._rust as m; print('rust ext ok:', m)"

# Lint + type + tests with coverage; this is the full suite
pytest -q --cov=hashsigs --cov-report=term-missing
```

If the Rust toolchain is not available, the above will fail on the rust-backed vector tests. See the “Test options” section for alternatives.

## Test options

You can choose between three categories:

- All Tests (vectors + rust-backed + lint + type + coverage) — fails if keccak or rust ext are missing
  - pip install -e '.[rust,dev]' && pip install pycryptodome
  - pytest -q

- Basic (pure Python functionality only; requires keccak provider, but no Rust extension)
  - pip install -e '.[dev]' pycryptodome
  - HASHSIGS_BUILD_RUST=0 pytest -q -m "not requires_rust"

- Basic (no keccak) — internal consistency tests only using hashlib.sha3_256; no vectors
  - pip install -e '.[dev]'
  - pytest -q -m "not vectors"

## Troubleshooting

- pysha3 build fails on Python 3.13 (macOS) with missing pystrhex.h
  - Symptom: fatal error: 'pystrhex.h' file not found when building _pysha3
  - Fix: install pycryptodome instead (preferred). Example: pip install pycryptodome
  - Alternative: use Python 3.11/3.12 where pysha3 wheels may exist, or wait for pysha3 to add 3.13 support

- Rust extension won’t build/import
  - Ensure Rust toolchain is installed: curl https://sh.rustup.rs -sSf | sh (or brew install rust)
  - On macOS, ensure Xcode Command Line Tools are installed: xcode-select --install
  - Clean and rebuild in your venv:
    - pip uninstall -y hashsigs; pip install -e .[rust,dev]
    - python -c "import hashsigs._rust as m; print('rust ext ok', m)"
  - If it still fails, you can run Basic tests while you investigate: HASHSIGS_BUILD_RUST=0 pytest -q -m "not requires_rust"

## Usage example

```python
from hashsigs import WOTSPlus

# Prefer the Rust backend if available; falls back to Python keccak provider if not
wots = WOTSPlus.keccak256(prefer_rust=True)

# Derive a keypair from a 32-byte seed
seed = bytes([1]) * 32
pk, sk = wots.generate_key_pair(seed)

# Sign and verify a 32-byte message
msg = bytes([2]) * 32
sig = wots.sign(sk, msg)
assert wots.verify(pk, msg, sig)
print("Signature verifies!")
```

### Quick self-check (from shell)

Run a one-liner to confirm the package imports, the Rust extension is available (optional), and basic operations work:

```bash
python - <<'PY'
from hashsigs import WOTSPlus
try:
    import hashsigs._rust as _
    print('Rust extension: available')
except Exception:
    print('Rust extension: not available (falling back to Python)')

wots = WOTSPlus.keccak256(prefer_rust=True)
seed = bytes([1]) * 32
pk, sk = wots.generate_key_pair(seed)
msg = bytes([2]) * 32
sig = wots.sign(sk, msg)
print('verify:', wots.verify(pk, msg, sig))
PY
```

## Rust backend

We now depend on the public crate and repository:
- Crate: hashsigs-rs = "0.0.2"
- Repo: https://github.com/QuipNetwork/hashsigs-rs

The Python bindings (PyO3) will attempt to build against the published crate during installation. If the build fails, the package still installs and falls back to pure Python.

## License

AGPL-3.0-or-later; see COPYING

