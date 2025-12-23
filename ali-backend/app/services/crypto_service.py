import os
import base64
from google.cloud import kms_v1
from cryptography.fernet import Fernet


class CryptoService:
    """
    CryptoService uses Google Cloud KMS to encrypt/decrypt data encryption keys (DEKs)
    and uses Fernet (symmetric encryption) to encrypt/decrypt credentials with those DEKs.
    """

    def __init__(self) -> None:
        """
        Initialize the KMS client and load the KMS key resource name from environment.

        Expects environment variable `KMS_KEY_ID` to contain the full resource name of the
        CryptoKey to use, e.g.:
        "projects/PROJECT_ID/locations/global/keyRings/RING_NAME/cryptoKeys/KEY_NAME"
        """
        self._client = kms_v1.KeyManagementServiceClient()
        self.kms_key_id = os.getenv("KMS_KEY_ID")
        if not self.kms_key_id:
            raise RuntimeError("KMS_KEY_ID environment variable is not set")

    def _get_dek(self) -> bytes:
        """
        Generate a new Fernet DEK (Data Encryption Key).

        Returns:
            bytes: URL-safe base64-encoded 32-byte key as produced by Fernet.generate_key().
        """
        return Fernet.generate_key()

    def encrypt_credential(self, plaintext: str) -> dict:
        """
        Encrypt a plaintext credential.

        Steps:
        1. Generate a fresh DEK.
        2. Encrypt the plaintext with the DEK using Fernet.
        3. Encrypt the DEK using Google Cloud KMS.
        4. Return base64-encoded ciphertext and encrypted DEK.

        Args:
            plaintext (str): The plaintext credential to encrypt.

        Returns:
            dict: {
                'ciphertext': <base64_str>,
                'encrypted_dek': <base64_str>
            }
        """
        if plaintext is None:
            raise ValueError("plaintext must not be None")

        # Generate DEK and encrypt the plaintext
        dek = self._get_dek()  # bytes
        f = Fernet(dek)
        token = f.encrypt(plaintext.encode("utf-8"))  # bytes

        # Encrypt DEK with KMS
        encrypt_response = self._client.encrypt(
            request={"name": self.kms_key_id, "plaintext": dek}
        )
        encrypted_dek_bytes = encrypt_response.ciphertext

        # Return both pieces base64-encoded (standard base64)
        ciphertext_b64 = base64.b64encode(token).decode("utf-8")
        encrypted_dek_b64 = base64.b64encode(encrypted_dek_bytes).decode("utf-8")

        return {"ciphertext": ciphertext_b64, "encrypted_dek": encrypted_dek_b64}

    def decrypt_credential(self, payload: dict) -> str:
        """
        Decrypt a credential payload produced by `encrypt_credential`.

        Args:
            payload (dict): Must contain 'encrypted_dek' and 'ciphertext' as base64 strings.

        Returns:
            str: The original plaintext credential.
        """
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dict with 'encrypted_dek' and 'ciphertext'")

        encrypted_dek_b64 = payload.get("encrypted_dek")
        ciphertext_b64 = payload.get("ciphertext")

        if not encrypted_dek_b64 or not ciphertext_b64:
            raise ValueError("payload must contain both 'encrypted_dek' and 'ciphertext'")

        # Decode the encrypted DEK and decrypt it with KMS
        encrypted_dek_bytes = base64.b64decode(encrypted_dek_b64)
        decrypt_response = self._client.decrypt(
            request={"name": self.kms_key_id, "ciphertext": encrypted_dek_bytes}
        )
        dek = decrypt_response.plaintext  # bytes

        # Use the DEK to decrypt the ciphertext
        token = base64.b64decode(ciphertext_b64)
        f = Fernet(dek)
        plaintext_bytes = f.decrypt(token)

        return plaintext_bytes.decode("utf-8")