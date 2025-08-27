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

from . import core as _core

WOTSPlus = _core.WOTSPlus
PublicKey = _core.PublicKey
HASH_LEN = _core.HASH_LEN
MESSAGE_LEN = _core.MESSAGE_LEN
CHAIN_LEN = _core.CHAIN_LEN
NUM_MESSAGE_CHUNKS = _core.NUM_MESSAGE_CHUNKS
NUM_CHECKSUM_CHUNKS = _core.NUM_CHECKSUM_CHUNKS
NUM_SIGNATURE_CHUNKS = _core.NUM_SIGNATURE_CHUNKS
SIGNATURE_SIZE = _core.SIGNATURE_SIZE
PUBLIC_KEY_SIZE = _core.PUBLIC_KEY_SIZE


__all__ = [
    "WOTSPlus",
    "PublicKey",
    "HASH_LEN",
    "MESSAGE_LEN",
    "CHAIN_LEN",
    "NUM_MESSAGE_CHUNKS",
    "NUM_CHECKSUM_CHUNKS",
    "NUM_SIGNATURE_CHUNKS",
    "SIGNATURE_SIZE",
    "PUBLIC_KEY_SIZE",
]
