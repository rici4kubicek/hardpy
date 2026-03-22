# Copyright (c) 2026 Everypin
# GNU General Public License v3.0 (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

import os
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from hardpy.common.config import ConfigManager


class AuthAdapter(ABC):
    """Generic login adapter interface."""

    @abstractmethod
    def authenticate(self, username: str, password: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def authenticate_token(self, token: str) -> Optional[str]:
        raise NotImplementedError


@dataclass
class BasicCredentialsAuthAdapter(AuthAdapter):
    """Simple adapter for local username/password plus optional token."""

    def authenticate(self, username: str, password: str) -> bool:
        config = ConfigManager().config
        expected_user = config.database.user
        expected_pass = config.database.password
        if (secrets.compare_digest(username, expected_user) and
                secrets.compare_digest(password, expected_pass)):
            return True

        env_user = os.getenv("HARDPY_USERNAME")
        env_pass = os.getenv("HARDPY_PASSWORD")
        if env_user and env_pass:
            return (secrets.compare_digest(username, env_user) and
                    secrets.compare_digest(password, env_pass))

        return False

    def authenticate_token(self, token: str) -> Optional[str]:
        if not token:
            return None

        # token configured from environment for generic adapter usage
        env_token = os.getenv("HARDPY_AUTH_TOKEN")
        if env_token and secrets.compare_digest(token, env_token):
            env_user = os.getenv("HARDPY_USERNAME", ConfigManager().config.database.user)
            return env_user

        # fallback to StandCloud API key (as token if configured)
        sc_token = ConfigManager().config.stand_cloud.api_key
        if sc_token and secrets.compare_digest(token, sc_token):
            return ConfigManager().config.database.user

        # local token by default in DB user/password (not secure, used only for quick test)
        if secrets.compare_digest(token, "dev"):
            return ConfigManager().config.database.user

        return None


class AuthService:
    """Stateful auth service for API session management."""

    def __init__(self, adapter: AuthAdapter, auth_required: bool = False) -> None:
        self.adapter = adapter
        self.auth_required = auth_required
        self.current_user: Optional[str] = None
        self.session_token: Optional[str] = None

    def login(self, username: str, password: str) -> str:
        if not self.adapter.authenticate(username, password):
            raise ValueError("Invalid username or password")
        self.current_user = username
        self.session_token = secrets.token_hex(32)
        return self.session_token

    def login_with_token(self, token: str) -> str:
        user = self.adapter.authenticate_token(token)
        if not user:
            raise ValueError("Invalid token")
        self.current_user = user
        self.session_token = token
        return user

    def logout(self) -> None:
        self.current_user = None
        self.session_token = None

    def is_authenticated(self) -> bool:
        if not self.auth_required:
            return True
        return self.current_user is not None
