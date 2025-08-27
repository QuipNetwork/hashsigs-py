# Copyright (C) 2024 quip.network
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import unittest

from hashsigs import WOTSPlus


class TestPurePythonBasic(unittest.TestCase):
    def test_sha3_256_like_flow(self):
        # Note: hashlib.sha3_256 is not true keccak-256, but this basic test
        # is only checking internal consistency (sign/verify) in pure Python
        wots = WOTSPlus(lambda b: hashlib.sha3_256(b).digest())
        seed = bytes([1]) * 32
        pk, sk = wots.generate_key_pair(seed)
        msg = bytes([2]) * 32
        sig = wots.sign(sk, msg)
        self.assertTrue(wots.verify(pk, msg, sig))

    def test_param_overrides(self):
        # Use smaller parameters to keep the test fast and ensure overrides work
        # n must match hash output; here it's 32 (sha3_256)
        wots = WOTSPlus(lambda b: hashlib.sha3_256(b).digest(), w=16, n=32, m=32)
        seed = bytes([3]) * 32
        pk, sk = wots.generate_key_pair(seed)
        msg = bytes([4]) * 32
        sig = wots.sign(sk, msg)
        self.assertTrue(wots.verify(pk, msg, sig))


if __name__ == "__main__":
    unittest.main()
