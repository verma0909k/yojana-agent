"""Encrypted Document Vault: Secure storage for citizen certificates under data/vault/<user_id>/
using Fernet symmetric encryption and per-user metadata isolation.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional
import uuid
from cryptography.fernet import Fernet
from shared.config import VAULT_DIR, VAULT_KEY
from shared.schemas import DocumentExtraction, StoredDocumentMetadata


def _get_or_create_fernet_key() -> bytes:
    """Returns Fernet encryption key from env or auto-generated local key file."""
    if VAULT_KEY:
        try:
            return VAULT_KEY.encode("utf-8")
        except Exception:
            pass

    key_file = VAULT_DIR / ".vault_key"
    if key_file.exists():
        return key_file.read_bytes().strip()

    new_key = Fernet.generate_key()
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(new_key)
    except Exception:
        pass
    return new_key


class DocumentVault:
    """Manages encrypted document files and metadata scoped strictly by user_id."""

    def __init__(self, base_vault_dir: Optional[Path] = None, fernet_key: Optional[bytes] = None):
        self.base_dir = Path(base_vault_dir) if base_vault_dir else VAULT_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        key = fernet_key or _get_or_create_fernet_key()
        self.fernet = Fernet(key)

    def _user_dir(self, user_id: str) -> Path:
        clean_user = "".join(c for c in user_id if c.isalnum() or c in ("-", "_")) or "default_citizen"
        d = self.base_dir / clean_user
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _meta_path(self, user_id: str) -> Path:
        return self._user_dir(user_id) / "metadata.json"

    def _load_metadata_map(self, user_id: str) -> dict[str, dict]:
        p = self._meta_path(user_id)
        if not p.exists():
            return {}
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_metadata_map(self, user_id: str, data: dict[str, dict]):
        p = self._meta_path(user_id)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_document(
        self,
        user_id: str,
        file_bytes: bytes,
        filename: str,
        extraction: DocumentExtraction,
        mime_type: str = "image/jpeg",
        linked_scheme_ids: Optional[list[str]] = None,
    ) -> StoredDocumentMetadata:
        """Encrypts file_bytes with Fernet, stores in data/vault/<user_id>/<doc_id>.enc,
        and saves indexed metadata.
        """
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        user_dir = self._user_dir(user_id)
        encrypted_bytes = self.fernet.encrypt(file_bytes)

        enc_path = user_dir / f"{doc_id}.enc"
        enc_path.write_bytes(encrypted_bytes)

        # Average field confidence
        conf_scores = [fc.confidence for fc in extraction.per_field_confidence]
        avg_conf = sum(conf_scores) / len(conf_scores) if conf_scores else 0.95

        now_iso = datetime.now(timezone.utc).isoformat()
        metadata = StoredDocumentMetadata(
            doc_id=doc_id,
            user_id=user_id,
            filename=filename,
            doc_type=extraction.doc_type,
            holder_name=extraction.holder_name,
            issue_date=extraction.issue_date,
            expiry_date=extraction.expiry_date,
            income_amount=extraction.income_amount,
            id_last4=extraction.id_last4,
            linked_scheme_ids=linked_scheme_ids or [],
            confidence=round(avg_conf, 2),
            created_at=now_iso,
            file_path=str(enc_path),
            mime_type=mime_type,
        )

        all_meta = self._load_metadata_map(user_id)
        all_meta[doc_id] = metadata.model_dump()
        self._save_metadata_map(user_id, all_meta)

        return metadata

    def get_document_bytes(self, user_id: str, doc_id: str) -> tuple[bytes, StoredDocumentMetadata]:
        """Reads encrypted document file and returns decrypted plaintext bytes alongside metadata."""
        all_meta = self._load_metadata_map(user_id)
        if doc_id not in all_meta:
            raise FileNotFoundError(f"Document '{doc_id}' not found for user '{user_id}'.")

        meta = StoredDocumentMetadata.model_validate(all_meta[doc_id])
        enc_path = Path(meta.file_path)
        if not enc_path.exists():
            raise FileNotFoundError(f"Encrypted file not found on disk at {enc_path}.")

        encrypted_bytes = enc_path.read_bytes()
        plaintext_bytes = self.fernet.decrypt(encrypted_bytes)
        return plaintext_bytes, meta

    def list_documents(self, user_id: str) -> list[StoredDocumentMetadata]:
        """Returns all documents belonging to user_id."""
        all_meta = self._load_metadata_map(user_id)
        return [StoredDocumentMetadata.model_validate(d) for d in all_meta.values()]

    def delete_document(self, user_id: str, doc_id: str) -> bool:
        """Permanently deletes document file and metadata."""
        all_meta = self._load_metadata_map(user_id)
        if doc_id not in all_meta:
            return False

        meta = StoredDocumentMetadata.model_validate(all_meta[doc_id])
        enc_path = Path(meta.file_path)
        if enc_path.exists():
            enc_path.unlink()

        del all_meta[doc_id]
        self._save_metadata_map(user_id, all_meta)
        return True

    def delete_user_vault(self, user_id: str) -> bool:
        """Wipes entire encrypted vault for user_id (Right to Erasure compliance)."""
        user_dir = self._user_dir(user_id)
        if user_dir.exists():
            for f in user_dir.iterdir():
                if f.is_file():
                    f.unlink()
            user_dir.rmdir()
            return True
        return False
