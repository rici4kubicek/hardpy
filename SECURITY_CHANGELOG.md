# CHANGELOG - Security Fix

## [1.0.0-security-hotfix] - 2026-03-22

### 🔐 Security

#### Critical: Fixed Session Token Validation Vulnerability

**Issue:** Session tokens were generated but never validated on subsequent requests, allowing any authenticated user to access resources of other users.

**Root Cause:**
- `AuthService.is_authenticated()` only checked global server state, not client's token
- No per-request token validation existed
- Multiple users could be authenticated simultaneously through shared session state

**Fix:**
- Refactored `AuthService` to use per-token session storage (`sessions: dict[str, SessionInfo]`)
- Implemented `validate_session_token()` method for per-request validation
- Added FastAPI dependency injection (`get_current_user`) for automatic token validation
- Token extraction from request headers (`Authorization: Bearer` or `x-session-token`)
- Session timeout validation on every request

**Breaking Changes:**
- All authenticated API requests now **require** a valid session token
- Clients must update to include Authorization header or x-session-token header
- Format: `Authorization: Bearer <session_token>` (recommended)

**Protected Endpoints (now require token):**
- `POST /api/set_test_config/{config_name}`
- `GET /api/start`
- `GET /api/stop`
- `GET /api/collect`

**Migration Guide:**

Before:
```javascript
fetch('/api/start')  // Would work due to vulnerability
```

After:
```javascript
fetch('/api/start', {
    headers: {
        'Authorization': 'Bearer ' + sessionToken
    }
})
```

**Files Modified:**
- `hardpy/hardpy_panel/auth.py` - Complete refactoring of session management
- `hardpy/hardpy_panel/api.py` - Added per-request token validation

**References:**
- CWE-384: Session Fixation
- CWE-287: Improper Authentication
- OWASP: Session Management

### 📝 Documentation

- Added `SECURITY_FIX.md` - Detailed technical explanation
- Added `SECURITY_FIX_SUMMARY.md` - High-level summary and migration guide  
- Added `test_security_fix.py` - Automated test script

### ✅ Testing

Verify the fix works:
```bash
python test_security_fix.py
```

Manual testing:
```bash
# 1. Login
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

