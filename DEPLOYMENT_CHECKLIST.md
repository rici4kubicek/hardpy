# Security Fix Deployment Checklist

**Project:** HardPy  
**Issue:** Critical - Session Token Validation Vulnerability  
**Status:** Ready for Deployment  
**Date:** 2026-03-22

---

## ✅ Pre-Deployment Phase (Dev Team)

### Code Review
- [ ] Review `hardpy/hardpy_panel/auth.py` changes
  - [ ] Verify `SessionInfo` dataclass implementation
  - [ ] Verify `sessions` dictionary management
  - [ ] Verify `validate_session_token()` logic
  - [ ] Verify token generation uses `secrets.token_hex(32)`
  - [ ] Verify timeout validation logic
  
- [ ] Review `hardpy/hardpy_panel/api.py` changes
  - [ ] Verify `get_session_token()` function
  - [ ] Verify `get_current_user()` dependency function
  - [ ] Verify Bearer token extraction (`Authorization` header)
  - [ ] Verify custom token header (`x-session-token`)
  - [ ] Verify all 4 protected endpoints use `Depends(get_current_user)`
  - [ ] Verify endpoints: `/api/start`, `/api/stop`, `/api/collect`, `/api/set_test_config`

### Testing
- [ ] Run Python syntax check: `python3 -m py_compile hardpy/hardpy_panel/auth.py hardpy/hardpy_panel/api.py`
- [ ] Run automated tests: `python test_security_fix.py`
  - [ ] Test 1: Unauthenticated request → 401
  - [ ] Test 2: Login → Get session_token
  - [ ] Test 3: Valid token → 200 OK
  - [ ] Test 4: Invalid token → 401
  - [ ] Test 5: Alternative header → Works
  - [ ] Test 6: Logout → Invalidates
  - [ ] Test 7: Old token after logout → 401

- [ ] Manual testing (curl)
  - [ ] Test login endpoint
  - [ ] Test protected endpoint with valid token
  - [ ] Test protected endpoint without token (should be 401)
  - [ ] Test logout
  - [ ] Test protected endpoint after logout (should be 401)

- [ ] Test session timeout
  - [ ] Verify session timeout works
  - [ ] Verify old token after timeout returns 401

### Documentation Review
- [ ] Verify all documentation files created
  - [ ] SECURITY_FIX.md ✓
  - [ ] SECURITY_FIX_SUMMARY.md ✓
  - [ ] SECURITY_FIX_README.md ✓
  - [ ] SECURITY_FIX_IMPLEMENTATION.md ✓
  - [ ] SECURITY_CHANGELOG.md ✓
  - [ ] API_AUTH_MIGRATION.md ✓
  - [ ] SECURITY_FIX_INDEX.md ✓
  - [ ] test_security_fix.py ✓

- [ ] Review client migration guide
  - [ ] JavaScript examples present
  - [ ] Complete example class provided
  - [ ] Error handling explained
  - [ ] Token storage guidance provided

---

## ⚠️ Pre-Deployment Phase (QA/DevOps)

### Environment Setup
- [ ] Development environment ready
- [ ] Test environment ready
- [ ] Staging environment ready (if available)
- [ ] Production environment ready

### Backup & Rollback Plan
- [ ] Backup current `auth.py` → `auth.py.backup-[date]`
- [ ] Backup current `api.py` → `api.py.backup-[date]`
- [ ] Document rollback procedure
- [ ] Test rollback procedure
- [ ] Version control: Tag current release

### Client Communication
- [ ] Notify all API clients of breaking change
- [ ] Provide migration guide (API_AUTH_MIGRATION.md)
- [ ] Provide example code
- [ ] Set migration deadline
- [ ] Collect confirmation from all client teams

### Deployment Coordination
- [ ] All client teams ready to deploy
- [ ] Agreed on deployment window
- [ ] Agreed on deployment sequence
- [ ] Communication channels established
- [ ] Incident response team on standby

---

## 🚀 Deployment Phase

### Pre-Deployment Checks
- [ ] All automated tests passing
- [ ] All manual tests passing
- [ ] All documentation reviewed
- [ ] All client teams ready
- [ ] Rollback plan verified

### Deploy Updated Clients (First)
**Important:** Deploy clients FIRST, then server

- [ ] Step 1: Deploy updated clients to staging (if available)
  - [ ] Verify clients work with old server
  - [ ] Run smoke tests
  - [ ] Verify Authorization header sent correctly
  - [ ] Verify token included in all requests

- [ ] Step 2: After client verification, deploy to production
  - [ ] Deploy to all client deployments
  - [ ] Verify clients can login
  - [ ] Verify clients receive session tokens
  - [ ] Verify clients include Authorization header

- [ ] Verify clients are updated
  - [ ] Sample API calls show Authorization header
  - [ ] No 401 errors from token validation (still using old server)

### Deploy Updated Server (Second)
**Important:** Deploy server AFTER clients are updated

- [ ] Step 1: Deploy to staging (if available)
  - [ ] Deploy updated `auth.py`
  - [ ] Deploy updated `api.py`
  - [ ] Restart API server
  - [ ] Verify server starts without errors
  - [ ] Run smoke tests with valid token
  - [ ] Verify 401 returned without token
  - [ ] Verify 401 returned with invalid token
  - [ ] Verify session timeout works
  - [ ] Run `test_security_fix.py`

- [ ] Step 2: Deploy to production
  - [ ] Deploy updated `auth.py`
  - [ ] Deploy updated `api.py`
  - [ ] Restart API server
  - [ ] Monitor logs for errors
  - [ ] Monitor logs for 401 Unauthorized (expected for any non-updated clients)

---

## ✅ Post-Deployment Phase

### Immediate Checks (First Hour)
- [ ] API server running without errors
- [ ] Application logs clean (no exceptions)
- [ ] Authentication logs show successful logins
- [ ] Protected endpoints accessible with valid token
- [ ] Protected endpoints return 401 without token
- [ ] Session timeout working as expected

### Monitor Logs (First 24 Hours)
- [ ] Monitor for authentication errors
- [ ] Monitor for 401 Unauthorized errors (should be expected only for non-updated clients)
- [ ] Monitor for session-related exceptions
- [ ] Monitor for token validation errors

### Monitoring Metrics
- [ ] Login success rate: Should be > 99%
- [ ] Token validation success rate: Should be > 99%
- [ ] Error rate on protected endpoints: Should be < 1%
- [ ] Session timeout rate: Should be normal

### Verify Functionality
- [ ] Test login flow
  - [ ] POST /api/login returns session_token
  - [ ] Session_token is valid for 60 minutes (default)

- [ ] Test protected endpoints
  - [ ] POST /api/set_test_config/{name} requires token
  - [ ] GET /api/start requires token
  - [ ] GET /api/stop requires token
  - [ ] GET /api/collect requires token

- [ ] Test token validation
  - [ ] Valid token → Request succeeds (200)
  - [ ] Invalid token → Request fails (401)
  - [ ] No token → Request fails (401)
  - [ ] Expired token → Request fails (401)
  - [ ] Old token after logout → Request fails (401)

- [ ] Test logout
  - [ ] POST /api/logout invalidates token
  - [ ] Session no longer valid after logout

### Verify Non-Protected Endpoints Still Work
- [ ] GET /api/status (no token needed)
- [ ] GET /api/auth_status (no token needed)
- [ ] GET /api/hardpy_config (no token needed)
- [ ] POST /api/login (no token needed)

### Communication
- [ ] Notify all stakeholders: Deployment successful
- [ ] Send summary of changes
- [ ] Confirm all clients working
- [ ] No critical issues identified

---

## 🔄 Rollback Plan (If Needed)

**Use ONLY if critical issues occur**

### Step 1: Stop the Damage
- [ ] Take API offline (if necessary)
- [ ] Alert all users
- [ ] Activate incident response team

### Step 2: Restore Previous Version
- [ ] Copy backup: `cp auth.py.backup-[date] hardpy/hardpy_panel/auth.py`
- [ ] Copy backup: `cp api.py.backup-[date] hardpy/hardpy_panel/api.py`
- [ ] Restart API server
- [ ] Verify server starts successfully

### Step 3: Verify Rollback
- [ ] Test API endpoints
- [ ] Verify old clients still work (without Authorization header)
- [ ] Verify no authentication errors
- [ ] Notify users: Service restored

### Step 4: Post-Mortem
- [ ] Investigate what went wrong
- [ ] Fix issues in code
- [ ] Re-test before next deployment attempt
- [ ] Document lessons learned

---

## 📊 Deployment Verification Matrix

| Component | Before | After | Status |
|-----------|--------|-------|--------|
| Token validation | ❌ None | ✅ Per-request | ✓ |
| Session isolation | ❌ Global | ✅ Per-token | ✓ |
| Protected endpoints | ❌ Not validated | ✅ Validated | ✓ |
| 401 on missing token | ❌ No | ✅ Yes | ✓ |
| 401 on invalid token | ❌ No | ✅ Yes | ✓ |
| 401 on expired token | ❌ No | ✅ Yes | ✓ |
| Logout invalidates | ❌ No | ✅ Yes | ✓ |

---

## 🎯 Success Criteria

✅ **Deployment is successful if:**

1. **Code deployed without errors**
   - API server starts successfully
   - No exceptions in logs
   - All endpoints accessible

2. **Authentication working correctly**
   - Valid token → Access granted
   - Invalid token → 401 Unauthorized
   - Missing token → 401 Unauthorized
   - Expired token → 401 Unauthorized

3. **Clients updated and working**
   - All clients sending Authorization header
   - No 401 errors from token validation issues
   - Session management working

4. **Logging and monitoring**
   - Logs showing successful authentications
   - No unexpected error patterns
   - Session timeout working

5. **No data loss or corruption**
   - All user data intact
   - All test data intact
   - No rollback necessary

---

## ❌ Failure Criteria (Triggers Rollback)

❌ **Rollback if:**

1. API server crashes and won't restart
2. More than 10% of requests returning 500 errors
3. Authentication completely broken (all requests failing)
4. Database corruption detected
5. Multiple clients unable to access API
6. Security vulnerability not fixed or worsened

---

## 📞 Contact Information

### Deployment Team
- [ ] Tech Lead: ________________
- [ ] DevOps Lead: ________________
- [ ] QA Lead: ________________
- [ ] Security Lead: ________________

### Escalation
- [ ] On-call engineer: ________________
- [ ] Manager on call: ________________
- [ ] CTO/Tech Director: ________________

### Communication Channels
- [ ] Slack: ________________
- [ ] Email: ________________
- [ ] Phone: ________________

---

## 📝 Sign-Off

### Development Team
- [ ] Code review completed: _________________________ Date: _______
- [ ] Testing completed: _________________________ Date: _______
- [ ] Documentation reviewed: _________________________ Date: _______

### QA Team
- [ ] Integration tests passed: _________________________ Date: _______
- [ ] Load tests completed: _________________________ Date: _______
- [ ] Security verification completed: _________________________ Date: _______

### DevOps Team
- [ ] Infrastructure ready: _________________________ Date: _______
- [ ] Deployment plan approved: _________________________ Date: _______
- [ ] Monitoring configured: _________________________ Date: _______

### Management
- [ ] Approved for deployment: _________________________ Date: _______
- [ ] Risk assessment completed: _________________________ Date: _______
- [ ] Deployment window approved: _________________________ Date: _______

---

## 📋 Document Version

- **Document Version:** 1.0
- **Last Updated:** 2026-03-22
- **Valid Until:** 2026-06-22 (3 months)
- **Next Review Date:** 2026-06-22

---

**END OF DEPLOYMENT CHECKLIST**

For questions, refer to:
- Technical Details: `SECURITY_FIX.md`
- Client Migration: `API_AUTH_MIGRATION.md`
- Quick Reference: `SECURITY_FIX_README.md`

