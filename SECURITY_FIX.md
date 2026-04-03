# Security Fix: Per-Request Session Token Validation

## Problem
The previous authentication system had a critical security vulnerability:
- `AuthService` stored session state globally on the server (`self.current_user`)
- `is_authenticated()` only checked if `self.current_user` was not None
- Session tokens were generated and sent to clients but **never validated on subsequent requests**
- If Alice logged in, Bob accessing the same URL would immediately be authenticated as Alice

## Root Cause
The vulnerability existed in:
- `hardpy/hardpy_panel/auth.py:121-135` - `is_authenticated()` method
- `hardpy/hardpy_panel/api.py:209-213` - Endpoints calling `assert_authenticated()` without token validation

## Solution

### 1. AuthService Refactoring (`auth.py`)

Changed from stateful per-user to stateful session-based approach:

**Before:**
```python
class AuthService:
    def __init__(self, ...):
        self.current_user: Optional[str] = None
        self.session_token: Optional[str] = None
        
    def is_authenticated(self) -> bool:
        return self.current_user is not None  # Vulnerable!
```

**After:**
```python
@dataclass
class SessionInfo:
    username: str
    start_time: datetime
    token: str

class AuthService:
    def __init__(self, ...):
        self.sessions: dict[str, SessionInfo] = {}  # Per-token sessions
        
    def validate_session_token(self, token: str) -> Optional[str]:
        """Validates token and returns username, or None if invalid/expired"""
        # Checks token against stored sessions
        # Validates timeout
        # Returns username only if valid
```

### 2. Per-Request Token Validation (`api.py`)

Implemented FastAPI dependency injection for automatic token validation:

**Token Extraction:**
```python
def get_session_token(request: Request) -> Optional[str]:
    """Extracts token from:
    1. Authorization header (Bearer scheme): "Authorization: Bearer <token>"
    2. x-session-token header: "x-session-token: <token>"
    """
```

**Token Validation (Dependency):**
```python
def get_current_user(request: Request) -> str:
    """FastAPI dependency that validates token and returns username.
    Raises HTTPException(401) if token is invalid or missing."""
```

**Endpoint Protection:**
```python
@app.get("/api/start")
def start_pytest(
    args: Annotated[list[str] | None, Query()] = None, 
    user: Annotated[str, Depends(get_current_user)] = None  # Token validated automatically
) -> dict:
    # Token validated before this code runs
```

### 3. Session Management

- Multiple concurrent sessions per user are supported
- Each login generates a unique session token
- Sessions are isolated from each other
- Session timeout is validated on every request

## Migration Guide for Clients

### Before
Clients could ignore the token:
```javascript
// Old way (vulnerable)
fetch('/api/start')  // Works even without token!
```

### After
Clients **must** include session token in every request:

**Option 1: Authorization Header (Recommended)**
```javascript
fetch('/api/start', {
    headers: {
        'Authorization': 'Bearer ' + sessionToken
    }
})
```

**Option 2: x-session-token Header**
```javascript
fetch('/api/start', {
    headers: {
        'x-session-token': sessionToken
    }
})
```

## Login Flow

```
1. POST /api/login {"username": "user", "password": "pass"}
   ↓
2. Server: validates credentials, creates session
   Returns: {
       "status": "success",
       "user": "user",
       "session_token": "abc123..."  ← New unique token
   }
3. Client: stores session_token, includes in all subsequent requests
4. Server: validates token on every request using Depends(get_current_user)
```

## Logout Flow

```
1. POST /api/logout (with Authorization or x-session-token header)
   ↓
2. Server: removes session from sessions dict
   Returns: {"status": "success", "authenticated": false}
3. Client: discards session_token
4. Next request without valid token → 401 Unauthorized
```

## Files Modified

1. **hardpy/hardpy_panel/auth.py**
   - Added `SessionInfo` dataclass
   - Refactored `AuthService` to use session dict instead of single user state
   - Changed `login()` and `login_with_token()` to return session tokens
   - Added `validate_session_token()` for per-request validation
   - Changed `logout()` to accept token parameter

2. **hardpy/hardpy_panel/api.py**
   - Added `get_session_token()` to extract token from headers
   - Added `get_current_user()` dependency function for automatic validation
   - Updated all protected endpoints to use `Depends(get_current_user)`
   - Updated `/api/auth_status` to validate token from request
   - Updated `/api/logout` to invalidate specific token

## Protected Endpoints

The following endpoints now require valid session token:
- POST `/api/set_test_config/{config_name}`
- GET `/api/start`
- GET `/api/stop`
- GET `/api/collect`

## Testing

To verify the fix:

```bash
# 1. Login and get token
TOKEN=$(curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}' | jq -r '.session_token')

# 2. Request with valid token - should work
curl http://localhost:8000/api/start \
  -H "Authorization: Bearer $TOKEN"

# 3. Request without token - should return 401
curl http://localhost:8000/api/start
# Error: "User must be logged in with a valid session token"

# 4. Request with wrong token - should return 401
curl http://localhost:8000/api/start \
  -H "Authorization: Bearer invalid_token"
# Error: "User must be logged in with a valid session token"

# 5. Logout
curl -X POST http://localhost:8000/api/logout \
  -H "Authorization: Bearer $TOKEN"

# 6. Request with old token - should return 401
curl http://localhost:8000/api/start \
  -H "Authorization: Bearer $TOKEN"
# Error: "User must be logged in with a valid session token"
```

## Security Notes

- Session tokens are generated using `secrets.token_hex(32)` (cryptographically secure)
- Token validation uses `secrets.compare_digest()` to prevent timing attacks
- Session timeout is checked on every request
- Each client session is isolated and independent
- Multiple users cannot share the same session token

