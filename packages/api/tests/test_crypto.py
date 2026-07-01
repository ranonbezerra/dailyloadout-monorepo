"""At-rest crypto: HKDF key + MultiFernet legacy-decrypt rotation (hardening)."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, InvalidToken

from slate.infrastructure import crypto


class TestCryptoRotation:
    def test_roundtrip(self) -> None:
        assert crypto.decrypt_secret(crypto.encrypt_secret("s3cr3t")) == "s3cr3t"

    def test_legacy_ciphertext_still_decrypts(self) -> None:
        # A secret encrypted with the OLD single-SHA256 key must still decrypt via
        # the MultiFernet fallback, so existing MFA users don't lose access.
        legacy = Fernet(crypto._legacy_key()).encrypt(b"legacy-secret").decode()
        assert crypto.decrypt_secret(legacy) == "legacy-secret"

    def test_new_ciphertext_is_hkdf_not_legacy(self) -> None:
        # New ciphertext must NOT decrypt under the legacy key alone — proving the
        # HKDF (domain-separated) key is the primary one now.
        token = crypto.encrypt_secret("x").encode()
        with pytest.raises(InvalidToken):
            Fernet(crypto._legacy_key()).decrypt(token)

    def test_garbage_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Could not decrypt"):
            crypto.decrypt_secret("not-a-fernet-token")
