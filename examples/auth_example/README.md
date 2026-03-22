# HardPy Authentication Example

This example demonstrates how to enable and configure authentication in HardPy.

## Features

- Username/password-based login
- Token-based login
- Custom authentication adapters
- Configuration via `hardpy.toml`
- Environment variable overrides

## Custom Adapter Implementation

See [conftest.py](conftest.py) for an example `CustomAuthAdapter` that demonstrates:
- How to verify credentials against a backend system
- How to validate authentication tokens
- Integration with HardPy's auth system

The adapter can authenticate against:
- Databases (SQL, NoSQL)
- LDAP directories
- HTTP APIs
- Any custom authentication service

## Configuration

### Basic Setup (hardpy.toml)

```toml
[auth]
required = true
adapter = "conftest.CustomAuthAdapter"
```

With this configuration, HardPy will load `CustomAuthAdapter` from the example's conftest module.

**Parameters:**

- `required`: Set to `true` to require login before running tests
- `adapter`: Full Python module path to your authentication adapter class (format: `module.ClassName`)

### Built-in Adapter

`BasicCredentialsAuthAdapter` (default) supports:
- Username/password from `[database]` section (user/password fields)
- Username/password from environment: `HARDPY_USERNAME`, `HARDPY_PASSWORD`
- Token from environment: `HARDPY_AUTH_TOKEN`

## Environment Overrides

```bash
export HARDPY_AUTH_REQUIRED=true
export HARDPY_AUTH_ADAPTER="conftest.CustomAuthAdapter"
```

## Implementing Your Adapter

Create a class inheriting from `AuthAdapter`:

```python
from hardpy.hardpy_panel.auth import AuthAdapter
from typing import Optional

class YourAuthAdapter(AuthAdapter):
    def authenticate(self, username: str, password: str) -> bool:
        # Verify against your backend
        return verify_with_your_system(username, password)

    def authenticate_token(self, token: str) -> Optional[str]:
        # Verify token and return username
        return get_username_from_token(token)
```

Place it in a module and configure in `hardpy.toml`:

```toml
[auth]
required = true
adapter = "your_module.YourAuthAdapter"
```

## Running the Example

```bash
cd examples/auth_example
hardpy run
```

Open http://localhost:8000 and log in with (from CustomAuthAdapter):
- Username: `admin` / Password: `admin_password`
- Username: `operator` / Password: `op_password`
- Username: `viewer` / Password: `view_password`

Or use token login with:
- Token: `token_admin` (logs in as admin)
- Token: `token_operator` (logs in as operator)
- Token: `token_viewer` (logs in as viewer)

## API Endpoints

When auth is enabled:
- `POST /api/login` - Authenticate with username/password or token
- `POST /api/logout` - Logout
- `GET /api/auth_status` - Check current authentication status
- Protected: `/api/start`, `/api/stop`, `/api/collect`, `/api/set_test_config`

## See Also

- [HardPy Panel Documentation](../../docs/documentation/hardpy_panel.md#user-authentication-optional)
- [Authentication Module](../../hardpy/hardpy_panel/auth.py)

