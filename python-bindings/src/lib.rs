// Copyright (C) 2024 quip.network
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use hashsigs_rs as core;
use tiny_keccak::{Hasher, Keccak};

fn keccak256_hash(data: &[u8]) -> [u8; 32] {
    let mut hasher = Keccak::v256();
    let mut out = [0u8; 32];
    hasher.update(data);
    hasher.finalize(&mut out);
    out
}

#[pyclass]
struct WotsPlusKeccak256 {
    inner: core::WOTSPlus,
}

#[pymethods]
impl WotsPlusKeccak256 {
    #[new]
    fn new() -> Self {
        let inner = core::WOTSPlus::new(keccak256_hash);
        Self { inner }
    }

    #[staticmethod]
    fn hash_len() -> usize { core::constants::HASH_LEN }
    #[staticmethod]
    fn message_len() -> usize { core::constants::MESSAGE_LEN }
    #[staticmethod]
    fn chain_len() -> usize { core::constants::CHAIN_LEN }
    #[staticmethod]
    fn signature_size() -> usize { core::constants::SIGNATURE_SIZE }

    fn generate_key_pair(&self, private_seed: &[u8]) -> PyResult<(Py<PyBytes>, Py<PyBytes>)> {
        if private_seed.len() != core::constants::HASH_LEN {
            return Err(PyValueError::new_err(format!(
                "private_seed must be {} bytes", core::constants::HASH_LEN
            )));
        }
        let mut seed = [0u8; core::constants::HASH_LEN];
        seed.copy_from_slice(private_seed);
        let (pk, sk) = self.inner.generate_key_pair(&seed);
        Python::with_gil(|py| {
            let pk_bytes: Py<PyBytes> = PyBytes::new_bound(py, &pk.to_bytes()).unbind();
            let sk_bytes: Py<PyBytes> = PyBytes::new_bound(py, &sk).unbind();
            Ok((pk_bytes, sk_bytes))
        })
    }

    fn get_public_key(&self, private_key: &[u8]) -> PyResult<Py<PyBytes>> {
        if private_key.len() != core::constants::HASH_LEN {
            return Err(PyValueError::new_err(format!(
                "private_key must be {} bytes", core::constants::HASH_LEN
            )));
        }
        let mut sk = [0u8; core::constants::HASH_LEN];
        sk.copy_from_slice(private_key);
        let pk = self.inner.get_public_key(&sk);
        Python::with_gil(|py| Ok(PyBytes::new_bound(py, &pk.to_bytes()).unbind()))
    }

    fn sign(&self, private_key: &[u8], message: &[u8]) -> PyResult<Py<PyBytes>> {
        if private_key.len() != core::constants::HASH_LEN {
            return Err(PyValueError::new_err(format!(
                "private_key must be {} bytes", core::constants::HASH_LEN
            )));
        }
        if message.len() != core::constants::MESSAGE_LEN {
            return Err(PyValueError::new_err(format!(
                "message must be {} bytes", core::constants::MESSAGE_LEN
            )));
        }
        let mut sk = [0u8; core::constants::HASH_LEN];
        sk.copy_from_slice(private_key);
        let sig_segments = self.inner.sign(&sk, message);
        let mut sig = vec![0u8; core::constants::SIGNATURE_SIZE];
        for (i, seg) in sig_segments.iter().enumerate() {
            let start = i * core::constants::HASH_LEN;
            sig[start..start + core::constants::HASH_LEN].copy_from_slice(seg);
        }
        Python::with_gil(|py| Ok(PyBytes::new_bound(py, &sig).unbind()))
    }

    fn verify(&self, public_key: &[u8], message: &[u8], signature: &[u8]) -> PyResult<bool> {
        if public_key.len() != core::constants::PUBLIC_KEY_SIZE {
            return Err(PyValueError::new_err(format!(
                "public_key must be {} bytes", core::constants::PUBLIC_KEY_SIZE
            )));
        }
        if message.len() != core::constants::MESSAGE_LEN {
            return Err(PyValueError::new_err(format!(
                "message must be {} bytes", core::constants::MESSAGE_LEN
            )));
        }
        if signature.len() != core::constants::SIGNATURE_SIZE {
            return Err(PyValueError::new_err(format!(
                "signature must be {} bytes", core::constants::SIGNATURE_SIZE
            )));
        }
        let pk = match core::PublicKey::from_bytes(public_key) { Some(pk) => pk, None => return Ok(false) };
        // split signature
        let mut segs: Vec<[u8; core::constants::HASH_LEN]> = Vec::with_capacity(core::constants::NUM_SIGNATURE_CHUNKS);
        for i in 0..core::constants::NUM_SIGNATURE_CHUNKS {
            let start = i * core::constants::HASH_LEN;
            let mut seg = [0u8; core::constants::HASH_LEN];
            seg.copy_from_slice(&signature[start..start + core::constants::HASH_LEN]);
            segs.push(seg);
        }
        Ok(self.inner.verify(&pk, message, &segs))
    }
}

#[pymodule]
fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<WotsPlusKeccak256>()?;
    Ok(())
}

