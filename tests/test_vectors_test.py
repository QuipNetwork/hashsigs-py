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

import json
import os
import unittest
import pytest


from hashsigs import WOTSPlus

VECTORS_PATH = os.path.join(
    os.path.dirname(__file__),
    "test_vectors",
    "wotsplus_keccak256.json",
)


def _hex_to_bytes32(s: str) -> bytes:
    s = s[2:] if s.startswith("0x") else s
    return bytes(int(s[i : i + 2], 16) for i in range(0, 64, 2))


@pytest.mark.vectors
@pytest.mark.requires_keccak
class TestVectorsPurePython(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.wots = WOTSPlus.keccak256(prefer_rust=False)
        except ImportError as e:
            raise AssertionError(
                "keccak provider not found; install pysha3 or pycryptodome"
            ) from e

        with open(VECTORS_PATH, "r") as f:
            cls.vectors = json.load(f)

    def test_vectors(self):
        for name, vec in self.vectors.items():
            with self.subTest(vector=name):
                private_key = _hex_to_bytes32(vec["privateKey"])  # already 32B key
                message = _hex_to_bytes32(vec["message"])  # 32B message

                # expected public key is seed||hash (64 bytes hex)
                expected_pk_hex = vec["publicKey"][2:] if vec["publicKey"].startswith("0x") else vec["publicKey"]
                expected_pk = bytes(int(expected_pk_hex[i : i + 2], 16) for i in range(0, 128, 2))

                # expected signature is array of 32-byte hex segments
                expected_sig = b"".join(_hex_to_bytes32(seg) for seg in vec["signature"])  # len * 32

                pk = self.wots.get_public_key(private_key)
                self.assertEqual(pk.to_bytes(), expected_pk, f"Public key mismatch for {name}")

                sig = self.wots.sign(private_key, message)
                self.assertEqual(sig, expected_sig, f"Signature mismatch for {name}")

                self.assertTrue(self.wots.verify(pk, message, sig), f"Verify failed for {name}")


@pytest.mark.vectors
@pytest.mark.requires_keccak
@pytest.mark.requires_rust
class TestVectorsRustBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import hashsigs._rust  # noqa: F401
        except Exception as e:
            raise AssertionError("Rust extension not built; required for 'All Tests'") from e
        try:
            cls.wots = WOTSPlus.keccak256(prefer_rust=True)
        except ImportError as e:
            raise AssertionError(
                "keccak provider not found; install pysha3 or pycryptodome"
            ) from e
        with open(VECTORS_PATH, "r") as f:
            cls.vectors = json.load(f)

    def test_vectors(self):
        for name, vec in self.vectors.items():
            with self.subTest(vector=name):
                private_key = _hex_to_bytes32(vec["privateKey"])  # already 32B key
                message = _hex_to_bytes32(vec["message"])  # 32B message

                expected_pk_hex = vec["publicKey"][2:] if vec["publicKey"].startswith("0x") else vec["publicKey"]
                expected_pk = bytes(int(expected_pk_hex[i : i + 2], 16) for i in range(0, 128, 2))
                expected_sig = b"".join(_hex_to_bytes32(seg) for seg in vec["signature"])  # len * 32

                pk = self.wots.get_public_key(private_key)
                self.assertEqual(pk.to_bytes(), expected_pk, f"Public key mismatch for {name}")

                sig = self.wots.sign(private_key, message)
                self.assertEqual(sig, expected_sig, f"Signature mismatch for {name}")

                self.assertTrue(self.wots.verify(pk, message, sig), f"Verify failed for {name}")


if __name__ == "__main__":
    unittest.main()
