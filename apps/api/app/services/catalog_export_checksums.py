"""Exact-byte checksum helpers for catalog export artifacts."""

import hashlib


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
