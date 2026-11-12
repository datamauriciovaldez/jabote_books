"""Errores pensados para personas: llevan un código estable que la interfaz traduce."""
from __future__ import annotations

from typing import Any


class UserError(Exception):
    """Error con mensaje humano. `code` se traduce en web/static/i18n/*.json (claves errors.<code>)."""

    status = 400

    def __init__(self, code: str, detail: str = "", **params: Any) -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail
        self.params = params


class NotFound(UserError):
    status = 404


class Conflict(UserError):
    status = 409
