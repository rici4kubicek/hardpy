# Security Fix: Session Token Validation

## Status: ✅ COMPLETE

This directory contains a critical security fix for the HardPy API authentication system.

## What Was Fixed?

**Critical Vulnerability:** Session tokens were generated but never validated on subsequent requests.

- **Before:** Any request to protected endpoints would work if ANY user was logged in
- **After:** Every request requires a valid session token for the specific user

## Files Changed

### Core Changes
- `hardpy/hardpy_panel/auth.py` - Session management refactored
- `hardpy/hardpy_panel/api.py` - Per-request token validation added

### Documentation
- `SECURITY_FIX.md` - Technical details
- `SECURITY_FIX_SUMMARY.md` - Executive summary
- `SECURITY_CHANGELOG.md` - Change log
- `API_AUTH_MIGRATION.md` - Migration guide for API clients
- `test_security_fix.py` - Automated test script
- `SECURITY_FIX_README.md` - This file

## Quick Start

### For Developers

**Verify the fix:**
```bash
python test_security_fix.py
```

**Review the changes:**
```bash
# Auth service refactoring
git diff hardpy/hardpy_panel/auth.py

# API endpoint changes
git diff hardpy/hardpy_panel/api.py
```

### For API Clients

**Update your requests to include token:**

Before:
```javascript
fetch('/api/start')
```

After:
```javascript
fetch('/api/start', {
    headers: {
        'Authorization': 'Bearer ' + sessionToken
    }
})
```

See `API_AUTH_MIGRATION.md` for complete migration guide.

## Key Points

1. **Every authenticated request must include a session token**
   - In `Authorization: Bearer <token>` header, OR
   - In `x-session-token: <token>` header

2. **Tokens are validated on every request**
   - FastAPI automatically validates before endpoint is called
   - Invalid/expired tokens return 401 Unauthorized

3. **Session tokens are isolated per user**
   - Multiple users can have sessions simultaneously
   - Each session is completely independent
   - Logout invalidates only that specific token

4. **Breaking change - client updates required**
   - Old clients will receive 401 errors
   - See migration guide for update instructions

## Testing Scenarios

### ✓ Valid Request
```bash
curl http://localhost:8000/api/start \
  -H "Authorization: Bearer valid_token_abc123"
# Returns: 200 OK
```

### ✗ Missing Token
```bash
curl http://localhost:8000/api/start
# Returns: 401 Unauthorized
# Message: "User must be logged in with a valid session token"
```

### ✗ Invalid Token
```bash
curl http://localhost:8000/api/start \
  -H "Authorization: Bearer invalid_token"
# Returns: 401 Unauthorized
```

### ✓ Logout Invalidates Token
```bash
curl -X POST http://localhost:8000/api/logout \
  -H "Authorization: Bearer valid_token"
# Then subsequent request with same token returns 401
```

## Security Improvements

✅ Per-request token validation  
✅ Session isolation per user  
✅ Token timeout validation  
✅ Automatic logout on token expiry  
✅ Cryptographically secure token generation  
✅ Timing-attack resistant token comparison  
✅ No shared global authentication state  

## Protected Endpoints

These endpoints now require valid token:

| Endpoint | Method | Requires Token |
|----------|--------|---|
| `/api/set_test_config/{config_name}` | POST | ✅ |
| `/api/start` | GET | ✅ |
| `/api/stop` | GET | ✅ |
| `/api/collect` | GET | ✅ |
| `/api/login` | POST | ❌ |
| `/api/logout` | POST | Optional |
| `/api/auth_status` | GET | ❌ |
| `/api/status` | GET | ❌ |
| `/api/hardpy_config` | GET | ❌ |

## Migration Checklist

- [ ] Review this README
- [ ] Read SECURITY_FIX_SUMMARY.md for context
- [ ] Review API_AUTH_MIGRATION.md
- [ ] Update API client code to include Authorization header
- [ ] Run test_security_fix.py to verify
- [ ] Deploy updated clients
- [ ] Deploy updated server
- [ ] Monitor for 401 errors in logs (might indicate client issues)

## Frequently Asked Questions

### Q: Will this break existing clients?
**A:** Yes. Clients must update to include Authorization header. See migration guide.

### Q: Do I need to update the database?
**A:** No. Sessions are stored in-memory server state. No database changes needed.

### Q: What happens if token expires?
**A:** Client receives 401 error and should prompt user to login again.

### Q: Can I use cookies instead of headers?
**A:** Currently only header-based tokens are supported. Cookies can be added in future.

### Q: How long do tokens last?
**A:** Default 60 minutes. Configurable in HardPy settings.

### Q: Is this production-ready?
**A:** Yes. This fix addresses a critical security vulnerability.

## Support

For issues or questions:
1. Check API_AUTH_MIGRATION.md first
2. Review test_security_fix.py for examples
3. Check HardPy documentation
4. File an issue with details

## Version

- Fixed Version: 1.0.0-security-hotfix
- Date: 2026-03-22
- Status: Production Ready

