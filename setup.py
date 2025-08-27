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

# Build Rust extension optionally. If building fails or setuptools-rust is missing,
# installation will still succeed with pure Python.
# Users can set HASHSIGS_BUILD_RUST=0 to skip building the extension.

build_rust = os.environ.get("HASHSIGS_BUILD_RUST", "1") != "0"

rust_extensions = []
if build_rust:
    try:
        from setuptools_rust import RustExtension, Binding
        rust_extensions = [
            RustExtension(
                "hashsigs._rust",
                path="python-bindings/Cargo.toml",
                binding=Binding.PyO3,
                debug=False,
                optional=True,
            )
        ]
    except Exception:
        rust_extensions = []

setup(
    rust_extensions=rust_extensions,
    zip_safe=False,
)
