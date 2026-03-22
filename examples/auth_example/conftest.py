# Copyright (c) 2026 Everypin
# GNU General Public License v3.0 (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
Pytest configuration and fixtures for authentication example.

This module demonstrates how to implement a custom authentication adapter
for HardPy to verify credentials against external systems.
"""

import pytest
from typing import Optional

from hardpy.hardpy_panel.auth import AuthAdapter


class CustomAuthAdapter(AuthAdapter):
    """
    Example custom authentication adapter.

    This adapter demonstrates how to implement your own authentication backend
    to verify credentials against an external system (e.g., database, LDAP, HTTP API).

    In production, you would replace the hardcoded credentials with actual
    lookups to your authentication system.
    """

    def authenticate(self, username: str, password: str) -> bool:
        """
        Verify username and password credentials.

        Args:
            username: The username to verify
            password: The password to verify

        Returns:
            True if credentials are valid, False otherwise

        Examples:
            - Query a database: db.query('SELECT * FROM users WHERE username=?', username)
            - Call LDAP: ldap_connection.authenticate(username, password)
            - Call HTTP API: requests.post('https://auth-service.example.com/verify', ...)
        """
        # Example: simple hardcoded credentials (replace with your backend)
        valid_users = {
            "admin": "admin_password",
            "operator": "op_password",
            "viewer": "view_password",
        }

        if username not in valid_users:
            return False

        return password == valid_users[username]

    def authenticate_token(self, token: str) -> Optional[str]:
        """
        Verify an authentication token and return the username.

        Args:
            token: The token to verify

        Returns:
            Username if token is valid, None otherwise

        Examples:
            - Verify JWT: jwt.decode(token, secret)
            - Check Redis: redis.get(f'token:{token}')
            - Call HTTP API: requests.post('https://auth-service.example.com/verify-token', ...)
        """
        # Example: simple token mapping (replace with your backend)
        token_to_user = {
            "token_admin": "admin",
            "token_operator": "operator",
            "token_viewer": "viewer",
        }

        return token_to_user.get(token)


@pytest.fixture
def custom_adapter():
    """Fixture providing a custom auth adapter instance for tests."""
    return CustomAuthAdapter()
