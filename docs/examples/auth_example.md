# Authentication example

This example demonstrates how to enable and configure
[user authentication](../documentation/hardpy_panel.md#user-authentication-optional)
in the HardPy operator panel.

### Features

- Username/password login
- Token-based login
- Custom authentication adapter loaded from `conftest.py`
- Configuration via `hardpy.toml`
- Environment variable overrides

### How to start

1. Launch [CouchDB instance](../documentation/database.md#couchdb-instance).
2. Create a directory `<dir_name>` with the files described below.
3. Launch `hardpy run <dir_name>`.
4. Open http://localhost:8000 and log in with one of the credentials listed below.

### Configuration files

#### hardpy.toml

```toml
title = "HardPy TOML config"

[database]
user = "dev"
password = "dev"
host = "localhost"
port = 5984

[frontend]
host = "localhost"
port = 8000

[auth]
required = true
adapter = "conftest.CustomAuthAdapter"
```

Because `adapter` references `conftest.CustomAuthAdapter`, HardPy will load
the adapter class from `conftest.py` in the tests directory without any `PYTHONPATH` setup.

#### pytest.ini

```ini
[pytest]
addopts = --hardpy-pt
```

#### conftest.py

```python
from hardpy.hardpy_panel.auth import AuthAdapter
from typing import Optional

class CustomAuthAdapter(AuthAdapter):
    def authenticate(self, username: str, password: str) -> bool:
        valid_users = {
            "admin": "admin_password",
            "operator": "op_password",
        }
        return valid_users.get(username) == password

    def authenticate_token(self, token: str) -> Optional[str]:
        token_to_user = {
            "token_admin": "admin",
            "token_operator": "operator",
        }
        return token_to_user.get(token)
```

#### test_1.py

```python
import pytest

def test_example():
    assert True
```

### Credentials

**Username/password login:**

| Username   | Password         |
|------------|-----------------|
| `admin`    | `admin_password` |
| `operator` | `op_password`    |

**Token login:**

| Token            | Logs in as  |
|------------------|-------------|
| `token_admin`    | `admin`     |
| `token_operator` | `operator`  |

### Notes

- The logged-in username is automatically written to the test report.
  Calling [`set_user_name`](../documentation/pytest_hardpy.md#set_user_name) manually in tests will raise `DuplicateParameterError`.
- The `session_timeout` field in `[auth]` sets a session lifetime in minutes (default: no expiry).
