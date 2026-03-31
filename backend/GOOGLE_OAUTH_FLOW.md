# Google OAuth: Separate Register and Login Flow

## Overview

The Google OAuth implementation now has **separate registration and login flows** to ensure users must explicitly register before they can log in.

## API Endpoints

### 1. Register with Google
**Endpoint**: `GET /auth/google/register`

**Purpose**: Initiate Google OAuth for new user registration

**Flow**:
1. Frontend calls `/auth/google/register`
2. Backend returns Google auth URL with `state=register`
3. User authenticates with Google
4. Google redirects to `/auth/google/callback?code=...&state=register`
5. Backend checks if user already exists:
   - **If user exists**: Redirects to `/login?error=already_registered`
   - **If new user**: Creates account and redirects to `/auth/callback?token=...&registered=true`

### 2. Login with Google
**Endpoint**: `GET /auth/google/login`

**Purpose**: Initiate Google OAuth for existing user login

**Flow**:
1. Frontend calls `/auth/google/login`
2. Backend returns Google auth URL with `state=login`
3. User authenticates with Google
4. Google redirects to `/auth/google/callback?code=...&state=login`
5. Backend checks if user exists:
   - **If user doesn't exist**: Redirects to `/register?error=not_registered&provider=google`
   - **If user exists**: Creates JWT and redirects to `/auth/callback?token=...`

### 3. OAuth Callback
**Endpoint**: `GET /auth/google/callback`

**Parameters**:
- `code`: Authorization code from Google
- `state`: Either `"register"` or `"login"` to determine the flow

**Purpose**: Handle the OAuth callback and process registration or login

## Frontend Integration

### Registration Page

```typescript
// When user clicks "Register with Google" button
const handleGoogleRegister = async () => {
  try {
    const response = await fetch('http://localhost:8000/auth/google/register');
    const data = await response.json();
    
    // Redirect user to Google OAuth
    window.location.href = data.auth_url;
  } catch (error) {
    console.error('Failed to initiate Google registration:', error);
  }
};
```

### Login Page

```typescript
// When user clicks "Login with Google" button
const handleGoogleLogin = async () => {
  try {
    const response = await fetch('http://localhost:8000/auth/google/login');
    const data = await response.json();
    
    // Redirect user to Google OAuth
    window.location.href = data.auth_url;
  } catch (error) {
    console.error('Failed to initiate Google login:', error);
  }
};
```

### OAuth Callback Handler

```typescript
// In your /auth/callback route component
const AuthCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  useEffect(() => {
    const token = searchParams.get('token');
    const registered = searchParams.get('registered');
    const error = searchParams.get('error');
    
    if (token) {
      // Save token to localStorage or state management
      localStorage.setItem('auth_token', token);
      
      if (registered === 'true') {
        // Show success message for new registration
        navigate('/dashboard?message=registration_success');
      } else {
        // Regular login
        navigate('/dashboard');
      }
    } else if (error) {
      // Handle errors (shouldn't happen here, but just in case)
      navigate('/login?error=' + error);
    }
  }, [searchParams, navigate]);
  
  return <div>Processing authentication...</div>;
};
```

### Error Handling on Login Page

```typescript
// In your login page
const LoginPage = () => {
  const [searchParams] = useSearchParams();
  const error = searchParams.get('error');
  
  useEffect(() => {
    if (error === 'not_registered') {
      // Show message: "No account found. Please register first."
      showNotification({
        type: 'error',
        message: 'No account found with this Google account. Please register first.',
        action: {
          label: 'Go to Register',
          onClick: () => navigate('/register')
        }
      });
    }
  }, [error]);
  
  // ... rest of login page
};
```

### Error Handling on Register Page

```typescript
// In your register page
const RegisterPage = () => {
  const [searchParams] = useSearchParams();
  const error = searchParams.get('error');
  
  useEffect(() => {
    if (error === 'already_registered') {
      // Show message: "Account already exists. Please login."
      showNotification({
        type: 'info',
        message: 'An account with this Google account already exists. Please login instead.',
        action: {
          label: 'Go to Login',
          onClick: () => navigate('/login')
        }
      });
    }
  }, [error]);
  
  // ... rest of register page
};
```

## User Experience Flow

### Scenario 1: New User Registration
1. User visits `/register`
2. Clicks "Register with Google"
3. Redirected to Google login
4. Authenticates with Google
5. ✅ Account created
6. Redirected to `/auth/callback?token=...&registered=true`
7. Token saved, user logged in
8. Redirected to dashboard with welcome message

### Scenario 2: Existing User Login
1. User visits `/login`
2. Clicks "Login with Google"
3. Redirected to Google login
4. Authenticates with Google
5. ✅ User found in database
6. Redirected to `/auth/callback?token=...`
7. Token saved, user logged in
8. Redirected to dashboard

### Scenario 3: User Tries to Login Without Registering
1. User visits `/login`
2. Clicks "Login with Google"
3. Redirected to Google login
4. Authenticates with Google
5. ❌ User NOT found in database
6. Redirected to `/register?error=not_registered&provider=google`
7. Shows error: "No account found. Please register first."
8. User can click "Register with Google" to create account

### Scenario 4: User Tries to Register When Already Registered
1. User visits `/register`
2. Clicks "Register with Google"
3. Redirected to Google login
4. Authenticates with Google
5. ❌ User already exists in database
6. Redirected to `/login?error=already_registered`
7. Shows message: "Account already exists. Please login."
8. User can click "Login with Google" to access account

## Backend Response URLs

| Scenario | Redirect URL | Frontend Action |
|----------|--------------|-----------------|
| **Registration Success** | `/auth/callback?token=JWT&registered=true` | Save token, show welcome |
| **Login Success** | `/auth/callback?token=JWT` | Save token, redirect to dashboard |
| **Login Failed (Not Registered)** | `/register?error=not_registered&provider=google` | Show error, prompt to register |
| **Register Failed (Already Exists)** | `/login?error=already_registered` | Show message, prompt to login |

## Security Considerations

1. **State Parameter**: Uses OAuth `state` parameter to distinguish register vs login
2. **No Auto-Registration**: Users must explicitly register before logging in
3. **Clear Error Messages**: Users are guided to the correct action
4. **JWT Token**: Secure token-based authentication after successful auth
5. **Google ID as Identifier**: Uses `google_{google_id}` as unique identifier

## Testing

### Test Registration Flow
```bash
# 1. Get registration URL
curl http://localhost:8000/auth/google/register

# 2. Open the returned auth_url in browser
# 3. Complete Google authentication
# 4. Verify user is created in database
```

### Test Login Flow
```bash
# 1. Get login URL
curl http://localhost:8000/auth/google/login

# 2. Open the returned auth_url in browser
# 3. Complete Google authentication
# 4. Verify JWT token is returned
```

### Test Error Cases
1. Try to login without registering → Should redirect to register page
2. Try to register when already registered → Should redirect to login page

## Database Schema

Users registered with Google have:
- `phone`: `"google_{google_id}"` (unique identifier)
- `hashed_password`: `null` (no password needed)
- `name`: User's Google display name
- `avatar`: Google profile picture URL
- `role`: `buyer` (default)

## Migration from Old System

If you had users auto-created with the old system, they will continue to work. The new system only affects new registrations and logins going forward.
