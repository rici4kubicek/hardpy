# Session Token Validation Security Fix - Summary

## Vulnerability Description

**CVE Type:** Broken Authentication / Session Management  
**Severity:** Critical  
**CWE:** CWE-384 (Session Fixation), CWE-287 (Improper Authentication)

The HardPy API had a critical authentication vulnerability where:
- Session tokens were generated but **never validated** on subsequent requests
- The `is_authenticated()` method only checked if a user was logged in **on the server**, not validating the client's token
- If User A logged in, any request from User B to the same endpoint would be authenticated as User A
- No per-request token validation existed

### Vulnerable Code (Before Fix)

**auth.py (lines 121-135):**
```python
def is_authenticated(self) -> bool:
    if not self.auth_required:
        return True
    
    if self.current_user is None:
        return False
        
    # Check session timeout
    if self.session_timeout_minutes > 0 and self.session_start_time:
        elapsed = datetime.now() - self.session_start_time
        if elapsed > timedelta(minutes=self.session_timeout_minutes):
            self.logout()
            return False
            
    return True  # ← Vulnerable: No token validation!
```

**api.py (lines 209-213):**
```python
def assert_authenticated() -> None:  # ← No request parameter!
    if not app.state.auth_service.is_authenticated():  # ← Checks global state only
        raise HTTPException(...)
```

### Attack Scenario

1. **Alice logs in:** `POST /api/login` → Gets session_token: `abc123`
2. **Bob opens the same tab/URL:** All requests from the same browser session were authenticated because the server-side state didn't distinguish between users
3. **Result:** Bob gets access to Alice's test runs, can start/stop tests, etc.

## Fix Implementation

### 1. **AuthService Refactored** (`auth.py`)

**Changed from:**
- Single global `current_user` state
- Single global `session_token`
- Single global `session_start_time`

**To:**
- Dictionary of `sessions: dict[str, SessionInfo]`
- Each session token is unique and tied to a user
- Each session has its own timeout tracking

**New Methods:**
```python
def validate_session_token(self, token: str) -> Optional[str]:
    """
    Validates token and returns username if valid.
    Checks:
    - Token exists in sessions dict
    - Session hasn't expired
    Returns: username or None
    """
```

### 2. **Per-Request Token Validation** (`api.py`)

**Added:**
```python
def get_session_token(request: Request) -> Optional[str]:
    """Extract token from request headers"""
    
def get_current_user(request: Request) -> str:
    """FastAPI dependency for automatic token validation"""
```

**Applied to endpoints:**
```python
@app.get("/api/start")
def start_pytest(
    args: Annotated[list[str] | None, Query()] = None,
    user: Annotated[str, Depends(get_current_user)]  # ← Automatic validation
) -> dict:
    pass
```

### 3. **Token Extraction Methods**

Clients can provide tokens in two ways:

1. **Authorization Header (RFC 7235 - Recommended):**
   ```
   Authorization: Bearer <session_token>
   ```

2. **Custom Header:**
   ```
   x-session-token: <session_token>
   ```

## Protected Endpoints

Now require valid session token:
- ✓ POST `/api/set_test_config/{config_name}`
- ✓ GET `/api/start`
- ✓ GET `/api/stop`
- ✓ GET `/api/collect`

Endpoints that don't require authentication:
- GET `/api/status` (read-only, no sensitive data)
- GET `/api/hardpy_config` (read-only configuration)
- GET `/api/auth_status` (check authentication status)
- POST `/api/login` (to get token in first place)

## Client Migration Required

### Before (Vulnerable)
```javascript
// This would work regardless of who's logged in!
fetch('/api/start')
```

### After (Fixed)
```javascript
// Must include token in request
fetch('/api/start', {
    headers: {
        'Authorization': 'Bearer ' + sessionToken
    }
})
```

## Testing

### Manual Testing
```bash
# 1. Get token
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# 2. Use token (should work)
curl http://localhost:8000/api/start \
  -H "Authorization: Bearer <TOKEN>"

# 3. Without token (should fail with 401)
curl http://localhost:8000/api/start
# Error: "User must be logged in with a valid session token"
```

### Automated Testing
```bash
python test_security_fix.py
```

## Files Changed

1. **hardpy/hardpy_panel/auth.py**
   - Line 78: Added `SessionInfo` dataclass
   - Line 81-156: Refactored `AuthService` class
   - Line 89-106: Updated `login()` method
   - Line 108-125: Updated `login_with_token()` method
   - Line 127-152: New `validate_session_token()` method
   - Line 154-157: Updated `logout()` method
   - Line 159-162: Deprecated `is_authenticated` property

2. **hardpy/hardpy_panel/api.py**
   - Line 91-102: Added `get_session_token()` function
   - Line 105-129: Added `get_current_user()` dependency
   - Line 153: Updated `set_test_config()` signature
   - Line 174: Updated `start_pytest()` signature
   - Line 207: Updated `stop_pytest()` signature
   - Line 232: Updated `collect_pytest()` signature
   - Line 252-272: Updated `auth_status()` function
   - Line 308: Updated `logout()` signature

## Backwards Compatibility

⚠️ **BREAKING CHANGE** - Clients must be updated to send session token with authenticated requests.

Old clients will receive:
```json
{
  "detail": "User must be logged in with a valid session token"
}
```

## Session Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│                    Login Endpoint                        │
│  POST /api/login (username, password or token)          │
│              ↓                                           │
│    AuthService.login() or login_with_token()            │
│              ↓                                           │
│    Generate unique session token                        │
│    Store: sessions[token] = SessionInfo(user, time)    │
│              ↓                                           │
│    Return: {session_token: "abc123..."}                │
└─────────────────────────────────────────────────────────┘
                        ↓
        Client stores session_token
                        ↓
┌─────────────────────────────────────────────────────────┐
│          Protected Endpoint (e.g., /api/start)          │
│  GET /api/start + Authorization: Bearer abc123...      │
│              ↓                                           │
│    FastAPI Depends(get_current_user)                   │
│              ↓                                           │
│    get_session_token() extracts token from header      │
│              ↓                                           │
│    validate_session_token() checks:                    │
│      1. Token exists in sessions dict                  │
│      2. Session hasn't expired                         │
│      3. Return username                                │
│              ↓                                           │
│    If valid → Proceed, If invalid → 401 Unauthorized   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                    Logout Endpoint                       │
│  POST /api/logout + Authorization: Bearer abc123...    │
│              ↓                                           │
│    AuthService.logout(token)                           │
│              ↓                                           │
│    Delete: del sessions[token]                         │
│              ↓                                           │
│    Return: {authenticated: false}                       │
└─────────────────────────────────────────────────────────┘
                        ↓
    Token is now invalid, next request → 401
```

## Security Considerations

1. **Token Generation:** Using `secrets.token_hex(32)` (256 bits of entropy)
2. **Token Comparison:** Using `secrets.compare_digest()` (timing-attack resistant)
3. **Session Isolation:** Each token is completely independent
4. **Timeout Validation:** Checked on every request
5. **Logout:** Immediate session invalidation

## Deployment Notes

1. Update all API clients to include Authorization header
2. No database migrations needed
3. No configuration changes needed
4. In-memory sessions are lost on server restart (acceptable for this use case)

## Future Improvements

1. Consider persistent session storage (database) for production
2. Implement refresh tokens for long-lived sessions
3. Add session management UI (view active sessions, logout all)
4. Add request rate limiting per session
5. Add IP-based session validation

