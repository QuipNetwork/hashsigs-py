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

from __future__ import annotations

import math
from typing import Callable, Optional, List, Tuple, Protocol

# Defaults mirror the Rust constants, but are overridable in WOTSPlus(...)
HASH_LEN_DEFAULT = 32
MESSAGE_LEN_DEFAULT = HASH_LEN_DEFAULT
CHAIN_LEN_DEFAULT = 16
LG_CHAIN_LEN_DEFAULT = int(math.log2(CHAIN_LEN_DEFAULT))
NUM_MESSAGE_CHUNKS_DEFAULT = math.ceil(8 * HASH_LEN_DEFAULT / LG_CHAIN_LEN_DEFAULT)
NUM_CHECKSUM_CHUNKS_DEFAULT = math.floor(
    math.log(NUM_MESSAGE_CHUNKS_DEFAULT * (CHAIN_LEN_DEFAULT - 1), 2)
    / math.log(CHAIN_LEN_DEFAULT, 2)
) + 1
NUM_SIGNATURE_CHUNKS_DEFAULT = NUM_MESSAGE_CHUNKS_DEFAULT + NUM_CHECKSUM_CHUNKS_DEFAULT
SIGNATURE_SIZE_DEFAULT = NUM_SIGNATURE_CHUNKS_DEFAULT * HASH_LEN_DEFAULT
PUBLIC_KEY_SIZE_DEFAULT = HASH_LEN_DEFAULT * 2

# Expose module-level constants as defaults
HASH_LEN = HASH_LEN_DEFAULT
MESSAGE_LEN = MESSAGE_LEN_DEFAULT
CHAIN_LEN = CHAIN_LEN_DEFAULT
NUM_MESSAGE_CHUNKS = NUM_MESSAGE_CHUNKS_DEFAULT
NUM_CHECKSUM_CHUNKS = NUM_CHECKSUM_CHUNKS_DEFAULT
NUM_SIGNATURE_CHUNKS = NUM_SIGNATURE_CHUNKS_DEFAULT
SIGNATURE_SIZE = SIGNATURE_SIZE_DEFAULT
PUBLIC_KEY_SIZE = PUBLIC_KEY_SIZE_DEFAULT


class _RustBackendProtocol(Protocol):
    def generate_key_pair(self, private_seed: bytes) -> tuple[bytes, bytes]:
        ...

    def get_public_key(self, private_key: bytes) -> bytes:
        ...

    def sign(self, private_key: bytes, message: bytes) -> bytes:
        ...

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        ...


class PublicKey:
    def __init__(self, public_seed: bytes, public_key_hash: bytes):
        self.public_seed = public_seed
        self.public_key_hash = public_key_hash

    def to_bytes(self) -> bytes:
        return self.public_seed + self.public_key_hash

    @classmethod
    def from_bytes(cls, b: bytes) -> Optional["PublicKey"]:
        if len(b) != PUBLIC_KEY_SIZE:
            return None
        return cls(b[:HASH_LEN], b[HASH_LEN:])


class WOTSPlus:
    def __init__(
        self,
        hash_fn: Callable[[bytes], bytes],
        *,
        w: int = CHAIN_LEN_DEFAULT,
        len_1: Optional[int] = None,
        len_2: Optional[int] = None,
        n: int = HASH_LEN_DEFAULT,
        m: int = MESSAGE_LEN_DEFAULT,
    ):
        # Assign parameters
        self.hash_fn = hash_fn
        self.w = w
        self.n = n
        self.m = m
        self.lg_w = int(math.log2(self.w))
        self.len_1 = (
            len_1 if len_1 is not None else math.ceil(8 * self.n / self.lg_w)
        )
        self.len_2 = (
            len_2 if len_2 is not None else math.floor(
                math.log(self.len_1 * (self.w - 1), 2) / math.log(self.w, 2)
            )
            + 1
        )
        self.len = self.len_1 + self.len_2

        # Backend - pure Python by default; may be set by keccak256() factory
        # Narrow type when used; stored as object for optional import
        self._rust_backend: Optional["_RustBackendProtocol"] = None

    @classmethod
    def keccak256(
        cls,
        *,
        w: int = CHAIN_LEN_DEFAULT,
        len_1: Optional[int] = None,
        len_2: Optional[int] = None,
        n: int = HASH_LEN_DEFAULT,
        m: int = MESSAGE_LEN_DEFAULT,
        prefer_rust: bool = True,
    ) -> "WOTSPlus":
        # If the default parameters are used and rust is preferred, try rust first to avoid
        # requiring a Python keccak provider.
        match_defaults = (w == 16 and n == 32 and m == 32 and (len_1 is None or len_1 == 64) and (len_2 is None or len_2 == 3))
        if prefer_rust and match_defaults:
            try:
                import hashsigs._rust as _rust
                # Use a placeholder hash_fn; it won't be used when rust backend is active
                self = cls(lambda b: b, w=w, len_1=len_1, len_2=len_2, n=n, m=m)
                self._rust_backend = _rust.WotsPlusKeccak256()
                return self
            except Exception:
                pass
        # Fallback to Python keccak providers
        hash_fn = _python_keccak256()
        return cls(hash_fn, w=w, len_1=len_1, len_2=len_2, n=n, m=m)

    def _prf(self, seed: bytes, index: int) -> bytes:
        inp = bytes([0x03]) + seed + index.to_bytes(2, "big")
        return self.hash_fn(inp)

    def _xor(self, a: bytes, b: bytes) -> bytes:
        return bytes(x ^ y for x, y in zip(a, b))

    def _generate_randomization_elements(self, public_seed: bytes) -> List[bytes]:
        return [self._prf(public_seed, i) for i in range(self.len)]

    def _chain(self, prev: bytes, rand_elems: List[bytes], index: int, steps: int) -> bytes:
        out = prev
        for i in range(1, steps + 1):
            out = self.hash_fn(self._xor(out, rand_elems[i + index]))
        return out

    def _compute_message_hash_chain_indexes(self, message: bytes) -> List[int]:
        if len(message) != self.m:
            raise ValueError(f"Message length must be {self.m} bytes")
        idxs = [0] * self.len
        idx = 0
        for byte in message:
            idxs[idx] = byte >> 4
            idxs[idx + 1] = byte & 0x0F
            idx += 2
        checksum = 0
        for v in idxs[: self.len_1]:
            checksum += self.w - 1 - v
        for i in reversed(range(self.len_2)):
            shift = i * self.lg_w
            idxs[idx] = (checksum >> shift) & (self.w - 1)
            idx += 1
        return idxs

    def generate_key_pair(self, private_seed: bytes) -> Tuple[PublicKey, bytes]:
        if len(private_seed) != self.n:
            raise ValueError(f"private_seed must be {self.n} bytes")
        if self._rust_backend is not None:
            pk_bytes, sk_bytes = self._rust_backend.generate_key_pair(private_seed)
            pk = PublicKey.from_bytes(pk_bytes)
            if pk is None:
                raise ValueError("Invalid PublicKey from rust backend")
            return pk, sk_bytes
        private_key = self.hash_fn(private_seed)
        public_key = self.get_public_key(private_key)
        return public_key, private_key

    def get_public_key(self, private_key: bytes) -> PublicKey:
        if len(private_key) != self.n:
            raise ValueError(f"private_key must be {self.n} bytes")
        if self._rust_backend is not None:
            pk_bytes = self._rust_backend.get_public_key(private_key)
            pk = PublicKey.from_bytes(pk_bytes)
            if pk is None:
                raise ValueError("Invalid public key from rust backend")
            return pk
        public_seed = self._prf(private_key, 0)
        return self.get_public_key_with_public_seed(private_key, public_seed)

    def get_public_key_with_public_seed(self, private_key: bytes, public_seed: bytes) -> PublicKey:
        rand = self._generate_randomization_elements(public_seed)
        function_key = rand[0]
        segments = bytearray(self.len * self.n)
        for i in range(self.len):
            to_hash = function_key + self._prf(private_key, i + 1)
            sk_seg = self.hash_fn(to_hash)
            seg = self._chain(sk_seg, rand, 0, self.w - 1)
            start = i * self.n
            segments[start : start + self.n] = seg
        pk_hash = self.hash_fn(bytes(segments))
        return PublicKey(public_seed, pk_hash)

    def sign(self, private_key: bytes, message: bytes) -> bytes:
        if len(private_key) != self.n:
            raise ValueError(f"private_key must be {self.n} bytes")
        if len(message) != self.m:
            raise ValueError(f"message must be {self.m} bytes")
        if self._rust_backend is not None:
            return self._rust_backend.sign(private_key, message)
        public_seed = self._prf(private_key, 0)
        rand = self._generate_randomization_elements(public_seed)
        function_key = rand[0]
        chain_idxs = self._compute_message_hash_chain_indexes(message)
        sig = bytearray(self.len * self.n)
        for i, chain_idx in enumerate(chain_idxs):
            to_hash = function_key + self._prf(private_key, i + 1)
            sk_seg = self.hash_fn(to_hash)
            seg = self._chain(sk_seg, rand, 0, chain_idx)
            start = i * self.n
            sig[start : start + self.n] = seg
        return bytes(sig)

    def verify(self, public_key: PublicKey, message: bytes, signature: bytes) -> bool:
        if len(message) != self.m or len(signature) != self.len * self.n:
            return False
        if self._rust_backend is not None:
            return self._rust_backend.verify(public_key.to_bytes(), message, signature)
        rand = self._generate_randomization_elements(public_key.public_seed)
        chain_idxs = self._compute_message_hash_chain_indexes(message)
        segments = bytearray(self.len * self.n)
        for i, chain_idx in enumerate(chain_idxs):
            num_iter = (self.w - 1) - chain_idx
            start = i * self.n
            seg_in = signature[start : start + self.n]
            seg_out = self._chain(seg_in, rand, chain_idx, num_iter)
            segments[start : start + self.n] = seg_out
        computed = self.hash_fn(bytes(segments))
        return computed == public_key.public_key_hash


def _python_keccak256() -> Callable[[bytes], bytes]:
    # Try pycryptodome
    try:
        from Crypto.Hash import keccak as _k

        def _h(b: bytes) -> bytes:
            h = _k.new(digest_bits=256)
            h.update(b)
            return h.digest()

        return _h
    except Exception:
        pass
    # Try pysha3
    try:
        import sha3  # type: ignore

        def _h(b: bytes) -> bytes:
            k = sha3.keccak_256()
            k.update(b)
            return k.digest()

        return _h
    except Exception:
        raise ImportError("No keccak256 implementation found, please install pycryptodome or pysha3")
