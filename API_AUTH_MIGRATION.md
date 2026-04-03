# API Authentication Migration Guide

## Overview

The HardPy API now requires **per-request token validation** for all authenticated endpoints. This is a critical security fix for the session validation vulnerability.

## What Changed?

### Before (Vulnerable)
```javascript
// This would work regardless of authentication state
fetch('/api/start')
```

### After (Fixed)
```javascript
// Must include valid session token
fetch('/api/start', {
    headers: {
        'Authorization': 'Bearer ' + sessionToken
    }
})
```

## Migration Steps

### Step 1: Get Session Token on Login

After successful login, you'll receive a session token:

```javascript
async function login(username, password) {
    const response = await fetch('http://localhost:8000/api/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    });
    
    const data = await response.json();
    if (data.session_token) {
        // Store token for later use
        localStorage.setItem('session_token', data.session_token);
        return data.session_token;
    }
    throw new Error('Login failed');
}
```

### Step 2: Include Token in All Authenticated Requests

**Option A: Using Authorization Header (Recommended)**

```javascript
async function makeAuthenticatedRequest(endpoint, method = 'GET', body = null) {
    const token = localStorage.getItem('session_token');
    
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token  // ← Add this line
        }
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    const response = await fetch('http://localhost:8000' + endpoint, options);
    
    if (response.status === 401) {
        console.error('Unauthorized - token may have expired');
        // Handle logout/re-login
    }
    
    return response.json();
}

// Usage:
const result = await makeAuthenticatedRequest('/api/start');
```

**Option B: Using Custom Header**

```javascript
async function makeAuthenticatedRequest(endpoint, method = 'GET', body = null) {
    const token = localStorage.getItem('session_token');
    
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'x-session-token': token  // ← Alternative header
        }
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    const response = await fetch('http://localhost:8000' + endpoint, options);
    return response.json();
}
```

### Step 3: Handle Token Expiration

```javascript
async function makeRequestWithRefresh(endpoint, method = 'GET', body = null) {
    try {
        return await makeAuthenticatedRequest(endpoint, method, body);
    } catch (error) {
        if (error.response?.status === 401) {
            // Token expired or invalid
            console.log('Session expired, please log in again');
            localStorage.removeItem('session_token');
            // Redirect to login page
            window.location.href = '/login';
            throw error;
        }
        throw error;
    }
}
```

### Step 4: Logout

```javascript
async function logout() {
    const token = localStorage.getItem('session_token');
    
    await fetch('http://localhost:8000/api/logout', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + token
        }
    });
    
    // Clear stored token
    localStorage.removeItem('session_token');
}
```

## Protected Endpoints

The following endpoints **require** a valid session token:

- `POST /api/set_test_config/{config_name}` - Change test configuration
- `GET /api/start` - Start testing
- `GET /api/stop` - Stop testing
- `GET /api/collect` - Collect tests

## Public Endpoints

These endpoints **do not** require authentication:

- `GET /api/hardpy_config` - Get HardPy configuration
- `GET /api/status` - Get current status
- `POST /api/login` - User login
- `GET /api/auth_status` - Check authentication status

## Error Handling

### 401 Unauthorized

```javascript
if (response.status === 401) {
    // Token is invalid, expired, or missing
    // Actions:
    // 1. Clear stored token
    // 2. Redirect to login
    // 3. Ask user to log in again
}
```

### 403 Forbidden

```javascript
if (response.status === 403) {
    // User doesn't have permission for this action
    // Different from 401 (unauthenticated) - user is authenticated but not authorized
}
```

## Complete Example

```javascript
class HardPyClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.token = localStorage.getItem('session_token');
    }
    
    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/api/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            throw new Error('Login failed');
        }
        
        const data = await response.json();
        this.token = data.session_token;
        localStorage.setItem('session_token', this.token);
        return data;
    }
    
    async logout() {
        await this.request('/api/logout', { method: 'POST' });
        this.token = null;
        localStorage.removeItem('session_token');
    }
    
    async request(endpoint, options = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
                'Authorization': `Bearer ${this.token}`
            }
        });
        
        if (response.status === 401) {
            // Token expired
            this.logout();
            window.location.href = '/login';
            throw new Error('Session expired');
        }
        
        return response.json();
    }
    
    // Convenience methods
    async start(args = null) {
        return this.request('/api/start' + (args ? `?${args}` : ''));
    }
    
    async stop() {
        return this.request('/api/stop');
    }
    
    async collect() {
        return this.request('/api/collect');
    }
    
    async setTestConfig(configName) {
        return this.request(`/api/set_test_config/${configName}`, {
            method: 'POST'
        });
    }
}

// Usage
const client = new HardPyClient();

// Login
await client.login('admin', 'admin');

// Make authenticated requests
await client.start();
await client.stop();
await client.collect();

// Logout
await client.logout();
```

## Troubleshooting

### "User must be logged in with a valid session token"

**Cause:** Request doesn't include valid token  
**Solutions:**
1. Ensure you've called `login()` and received a token
2. Check token is stored in localStorage
3. Verify Authorization header is formatted correctly: `Bearer <token>`
4. Token might have expired (default 60 minutes)

### Token expires after X minutes

**Cause:** Session timeout is configured  
**Solution:** 
- Get fresh token by logging in again
- Or implement auto-refresh before expiry

### Cross-Origin (CORS) Issues

**Cause:** Browser blocks request from different origin  
**Solution:** Configure CORS properly in HardPy settings

## Security Notes

- **Always use HTTPS in production** (not just HTTP)
- **Never expose tokens** in URLs or logs
- **Store tokens securely** (httpOnly cookies are better than localStorage for web apps)
- **Include token in ALL authenticated requests**
- **Handle token expiration gracefully**

## Questions?

If you encounter issues migrating to the new authentication:
1. Check the error message carefully
2. Verify token is being sent in Authorization header
3. Ensure token is valid and not expired
4. Review this guide's examples

