# Backend Cookie Authentication Setup - Summary

## Changes Made

### 1. Backend API Changes (app/api/auth.py)

**Updated imports:**
- Added `Response, Cookie` from FastAPI for cookie handling

**Modified `get_current_user()` dependency:**
- **Before:** Read from `Authorization` header (`Bearer <token>`)
- **After:** Read from `auth_token` cookie (httpOnly)
- Returns 401 if cookie is missing

**Modified `verify_token()` endpoint:**
- Added `response: Response` parameter
- Sets httpOnly cookie on successful authentication:
  ```python
  response.set_cookie(
      key="auth_token",
      value=str(user.id),
      httponly=True,     # Prevents JavaScript access (XSS protection)
      samesite="lax",    # CSRF protection
      max_age=86400 * 30, # 30 days
      secure=False       # Set to True in production with HTTPS
  )
  ```

**Added `logout()` endpoint:**
- `POST /api/auth/logout`
- Clears the `auth_token` cookie
- Requires authentication (uses `get_current_user` dependency)

### 2. Test Fixtures (tests/conftest.py)

**Updated `client` fixture:**
- **Before:** Set Authorization header: `client.headers["Authorization"] = f"Bearer {test_user.id}"`
- **After:** Set cookie: `client.cookies.set("auth_token", str(test_user.id))`

### 3. Test Updates (tests/test_auth.py)

**Updated `test_verify_token_valid`:**
- Added cookie verification:
  ```python
  assert "auth_token" in response.cookies
  assert response.cookies["auth_token"] == str(user.id)
  ```

**Added new test `test_logout_clears_cookie`:**
- Verifies logout endpoint clears the authentication cookie

### 4. Frontend Configuration

**Created `.env.local`:**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Updated `lib/auth.ts`:**
- Removed localStorage token functions (getToken, setToken, removeToken)
- Added `credentials: "include"` to all fetch calls
- Removed manual Authorization header injection
- Cookie is automatically sent by browser

**Updated `lib/api.ts`:**
- Removed token import and manual injection
- Added `credentials: "include"` to fetch calls

**Updated `lib/hooks/use-auth.ts`:**
- Changed logout to call `authAPI.logout()` instead of removing localStorage

## Security Improvements

### Before (localStorage + Bearer tokens)
❌ Vulnerable to XSS attacks (JavaScript can read localStorage)
❌ Developer must manually attach token to requests
❌ Token visible in browser DevTools

### After (httpOnly cookies)
✅ **XSS Protection:** JavaScript cannot access httpOnly cookies
✅ **Automatic:** Browser automatically sends cookies with requests
✅ **CSRF Protection:** SameSite=lax prevents cross-site attacks
✅ **Secure:** Can enable HTTPS-only in production

## API Endpoints

| Endpoint | Method | Purpose | Cookie |
|----------|--------|---------|--------|
| `/api/auth/request-magic-link` | POST | Request magic link | - |
| `/api/auth/verify-token` | POST | Verify magic link | **Sets** auth_token |
| `/api/auth/logout` | POST | Logout user | **Clears** auth_token |
| All other endpoints | * | Protected routes | **Reads** auth_token |

## Testing Status

All tests should still pass because:
1. ✅ `test_auth.py` tests magic link flow (unchanged except added cookie verification)
2. ✅ `client` fixture updated to set cookies instead of headers
3. ✅ All protected endpoint tests use `client` fixture (automatically authenticated)
4. ✅ `verify_token` endpoint still returns same JSON (backward compatible)
5. ✅ Added new logout test

## Next Steps

1. Run backend tests to verify cookie authentication works
2. Start backend server: `cd backend && uvicorn app.main:app --reload`
3. Start frontend server: `cd frontend/job-automation-dashboard && npm run dev`
4. Test full auth flow:
   - Login → Verify → Profile → Dashboard
   - Check browser DevTools → Cookies → auth_token should be httpOnly
