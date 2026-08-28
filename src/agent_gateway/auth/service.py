"""API key authentication service."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from agent_gateway.auth.context import AuthContext, Role
from agent_gateway.config.settings import Settings


@dataclass(frozen=True)
class ApiKeyRecord:
    """Runtime mapping from hashed API key to auth context."""

    key_hash: str
    subject: str
    tenant_id: str
    role: Role


def hash_api_key(raw_key: str) -> str:
    """Return SHA-256 hex digest of an API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class AuthService:
    """Validate X-API-Key headers against configured hashed keys."""

    def __init__(self, settings: Settings) -> None:
        self._records = self._load_records(settings)

    @staticmethod
    def _load_records(settings: Settings) -> dict[str, ApiKeyRecord]:
        records: dict[str, ApiKeyRecord] = {}
        for entry in settings.api_key_entries:
            record = ApiKeyRecord(
                key_hash=entry.hash,
                subject=entry.subject,
                tenant_id=entry.tenant_id,
                role=Role(entry.role),
            )
            records[record.key_hash] = record
        return records

    def authenticate(self, raw_key: str | None) -> AuthContext | None:
        """Return auth context when the key is valid."""
        if not raw_key:
            return None
        digest = hash_api_key(raw_key)
        record = self._records.get(digest)
        if record is None:
            return None
        return AuthContext(
            subject=record.subject,
            tenant_id=record.tenant_id,
            role=record.role,
        )
