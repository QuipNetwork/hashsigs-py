# Copyright (C) 2024 quip.network
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from setuptools import setup
import os

# Smart Rust extension building:
# 1. If HASHSIGS_BUILD_RUST=0, skip Rust entirely (pure Python)
# 2. If HASHSIGS_BUILD_RUST=1, force Rust build (fail if it doesn't work)
# 3. If unset (default), try Rust first, fall back to pure Python if it fails

build_rust_env = os.environ.get("HASHSIGS_BUILD_RUST", "auto")

rust_extensions = []
if build_rust_env == "0":
    # Explicitly disabled
    print("hashsigs: Rust extension disabled by HASHSIGS_BUILD_RUST=0")
elif build_rust_env == "1":
    # Explicitly enabled - fail if it doesn't work
    try:
        from setuptools_rust import RustExtension, Binding
        rust_extensions = [
            RustExtension(
                "hashsigs._rust",
                path="python-bindings/Cargo.toml",
                binding=Binding.PyO3,
                debug=False,
                optional=False,  # Fail if Rust build fails
            )
        ]
        print("hashsigs: Building with Rust extension (forced)")
    except ImportError as e:
        raise RuntimeError(f"hashsigs: HASHSIGS_BUILD_RUST=1 but setuptools-rust not available: {e}")
else:
    # Auto mode - try Rust, fall back to pure Python
    try:
        from setuptools_rust import RustExtension, Binding
        import subprocess
        # Quick check if Rust toolchain is available
        subprocess.run(["rustc", "--version"], check=True, capture_output=True)
        rust_extensions = [
            RustExtension(
                "hashsigs._rust",
                path="python-bindings/Cargo.toml",
                binding=Binding.PyO3,
                debug=False,
                optional=True,  # Fall back to pure Python if build fails
            )
        ]
        print("hashsigs: Attempting to build with Rust extension (auto-detected)")
    except (ImportError, subprocess.CalledProcessError, FileNotFoundError):
        print("hashsigs: Rust toolchain not available, building pure Python version")
        rust_extensions = []

setup(
    rust_extensions=rust_extensions,
    zip_safe=False,
)
