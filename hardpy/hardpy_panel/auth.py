# Copyright (c) 2026 Everypin
# GNU General Public License v3.0 (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

import importlib
import importlib.util
import hashlib
import os
import secrets
import sys
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import ModuleType
from typing import Optional

from hardpy.common.config import ConfigManager
from hardpy.pytest_hardpy.pytest_call import set_user_name


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


        return None


@dataclass
class SessionInfo:
    """Session token information."""
    username: str
    start_time: datetime
    token: str


class AuthService:
    """Auth service for API session management with per-request token validation."""

    def __init__(self, adapter: AuthAdapter, auth_required: bool = False) -> None:
        self.adapter = adapter
        self.auth_required = auth_required
        self.session_timeout_minutes = ConfigManager().config.auth.session_timeout
        # Dict mapping session tokens to session info
        self.sessions: dict[str, SessionInfo] = {}

    def login(self, username: str, password: str) -> str:
        """Authenticate user with username/password and create session."""
        if not self.adapter.authenticate(username, password):
            raise ValueError("Invalid username or password")
        
        session_token = secrets.token_hex(32)
        self.sessions[session_token] = SessionInfo(
            username=username,
            start_time=datetime.now(),
            token=session_token,
        )
        
        # Set user name in test report
        try:
            set_user_name(username)
        except Exception:
            # Ignore if user name is already set
            pass
        return session_token

    def login_with_token(self, token: str) -> str:
        """Authenticate user with provided token and create session."""
        user = self.adapter.authenticate_token(token)
        if not user:
            raise ValueError("Invalid token")
        
        session_token = secrets.token_hex(32)
        self.sessions[session_token] = SessionInfo(
            username=user,
            start_time=datetime.now(),
            token=session_token,
        )
        
        # Set user name in test report
        try:
            set_user_name(user)
        except Exception:
            # Ignore if user name is already set
            pass
        return session_token

    def validate_session_token(self, token: Optional[str]) -> Optional[str]:
        """Validate session token and return username if valid, None otherwise."""
        if not self.auth_required:
            return "guest"

        if not token or token not in self.sessions:
            return None
        
        session = self.sessions[token]
        
        # Check session timeout
        if self.session_timeout_minutes > 0:
            elapsed = datetime.now() - session.start_time
            if elapsed > timedelta(minutes=self.session_timeout_minutes):
                del self.sessions[token]  # Invalidate expired session
                return None
        
        return session.username

    def logout(self, token: str) -> None:
        """Logout user by invalidating session token."""
        if token in self.sessions:
            del self.sessions[token]

    @property
    def is_authenticated(self) -> bool:
        """Deprecated: Use validate_session_token() instead for per-request validation."""
        # This property is kept for backwards compatibility but should not be used
        return not self.auth_required


def load_auth_adapter() -> AuthAdapter:
    """Load user-defined authentication adapter from module path."""
    config_manager = ConfigManager()
    config_adapter_path = config_manager.config.auth.adapter

    adapter_path = os.getenv("HARDPY_AUTH_ADAPTER", config_adapter_path)

    if "." not in adapter_path:
        raise ValueError("Auth adapter must be a module path to a class")

    module_name, class_name = adapter_path.rsplit(".", 1)

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise
        module = _import_module_from_tests_path(
            module_name,
            config_manager.tests_path,
        )
        if module is None:
            raise

    adapter_cls = getattr(module, class_name, None)

    if adapter_cls is None:
        tests_module = _import_module_from_tests_path(
            module_name,
            config_manager.tests_path,
            register_name=_make_tests_module_alias(module_name, config_manager.tests_path),
        )
        if tests_module is not None:
            module = tests_module
            adapter_cls = getattr(module, class_name, None)

    if adapter_cls is None:
        raise ImportError(f"Auth adapter class {class_name} not found in {module_name}")

    if not issubclass(adapter_cls, AuthAdapter):
        raise TypeError(
            f"Auth adapter {adapter_path} must inherit from AuthAdapter"
        )

    return adapter_cls()


def _import_module_from_tests_path(
    module_name: str,
    tests_path: Path,
    register_name: str | None = None,
) -> ModuleType | None:
    """Import module from configured tests directory when not on PYTHONPATH."""
    parts = module_name.split(".")
    module_file = tests_path.joinpath(*parts).with_suffix(".py")
    package_file = tests_path.joinpath(*parts, "__init__.py")

    source_path = module_file if module_file.exists() else package_file
    if not source_path.exists():
        return None

    spec_name = register_name or module_name
    spec = importlib.util.spec_from_file_location(spec_name, source_path)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec_name] = module
    spec.loader.exec_module(module)
    return module


def _make_tests_module_alias(module_name: str, tests_path: Path) -> str:
    module_hash = hashlib.sha1(str(tests_path).encode(), usedforsecurity=False).hexdigest()[:12]
    sanitized_module_name = module_name.replace(".", "_")
    return f"_hardpy_auth_{sanitized_module_name}_{module_hash}"


def make_auth_service() -> AuthService:
    config_manager = ConfigManager()
    config_auth_required = config_manager.config.auth.required

    auth_required_str = os.getenv("HARDPY_AUTH_REQUIRED", "").lower()
    if auth_required_str in ("1", "true", "yes", "on"):
        auth_required = True
    elif auth_required_str in ("0", "false", "no", "off"):
        auth_required = False
    else:
        auth_required = config_auth_required

    return AuthService(load_auth_adapter(), auth_required=auth_required)

