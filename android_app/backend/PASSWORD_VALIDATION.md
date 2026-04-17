# Password Strength Validation

## Backend Implementation

### Password Requirements

All passwords must meet the following criteria:

✅ **Minimum 8 characters**
✅ **At least one uppercase letter** (A-Z)
✅ **At least one lowercase letter** (a-z)
✅ **At least one digit** (0-9)
✅ **At least one special character** (!@#$%^&*(),.?":{}|<>)

### Backend Validation

The password validation is implemented in `schemas.py` using Pydantic validators. When a user tries to register with a weak password, the API will return a `422 Unprocessable Entity` error with a detailed message.

#### Example Error Response

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "password"],
      "msg": "Value error, Password must contain at least one uppercase letter",
      "input": "weakpassword123",
      "ctx": {
        "error": {}
      }
    }
  ]
}
```

### Testing Password Validation

```bash
# Test with weak password (will fail)
curl -X POST http://localhost:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+998901234567",
    "password": "weak",
    "name": "Test User",
    "role": "buyer"
  }'

# Test with strong password (will succeed)
curl -X POST http://localhost:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+998901234567",
    "password": "Strong@Pass123",
    "name": "Test User",
    "role": "buyer"
  }'
```

## Frontend Implementation

### React Password Strength Indicator

Here's a complete implementation for your frontend:

```typescript
// components/PasswordStrengthIndicator.tsx
import { useState, useEffect } from 'react';

interface PasswordStrength {
  score: number; // 0-5
  message: string;
  color: string;
  requirements: {
    minLength: boolean;
    hasUppercase: boolean;
    hasLowercase: boolean;
    hasNumber: boolean;
    hasSpecial: boolean;
  };
}

export const checkPasswordStrength = (password: string): PasswordStrength => {
  const requirements = {
    minLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
    hasSpecial: /[!@#$%^&*(),.?":{}|<>]/.test(password),
  };

  const score = Object.values(requirements).filter(Boolean).length;

  let message = '';
  let color = '';

  switch (score) {
    case 0:
    case 1:
      message = 'Very Weak';
      color = 'text-red-600';
      break;
    case 2:
      message = 'Weak';
      color = 'text-orange-600';
      break;
    case 3:
      message = 'Fair';
      color = 'text-yellow-600';
      break;
    case 4:
      message = 'Good';
      color = 'text-blue-600';
      break;
    case 5:
      message = 'Strong';
      color = 'text-green-600';
      break;
  }

  return { score, message, color, requirements };
};

interface PasswordStrengthIndicatorProps {
  password: string;
}

export const PasswordStrengthIndicator: React.FC<PasswordStrengthIndicatorProps> = ({
  password,
}) => {
  const [strength, setStrength] = useState<PasswordStrength>(
    checkPasswordStrength('')
  );

  useEffect(() => {
    setStrength(checkPasswordStrength(password));
  }, [password]);

  if (!password) return null;

  return (
    <div className="mt-2 space-y-2">
      {/* Strength Bar */}
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((level) => (
          <div
            key={level}
            className={`h-1 flex-1 rounded ${
              level <= strength.score
                ? strength.score <= 2
                  ? 'bg-red-600'
                  : strength.score === 3
                  ? 'bg-yellow-600'
                  : strength.score === 4
                  ? 'bg-blue-600'
                  : 'bg-green-600'
                : 'bg-gray-200'
            }`}
          />
        ))}
      </div>

      {/* Strength Label */}
      <p className={`text-sm font-medium ${strength.color}`}>
        {strength.message}
      </p>

      {/* Requirements Checklist */}
      <ul className="text-xs space-y-1">
        <li className={strength.requirements.minLength ? 'text-green-600' : 'text-gray-500'}>
          {strength.requirements.minLength ? '✓' : '○'} At least 8 characters
        </li>
        <li className={strength.requirements.hasUppercase ? 'text-green-600' : 'text-gray-500'}>
          {strength.requirements.hasUppercase ? '✓' : '○'} One uppercase letter
        </li>
        <li className={strength.requirements.hasLowercase ? 'text-green-600' : 'text-gray-500'}>
          {strength.requirements.hasLowercase ? '✓' : '○'} One lowercase letter
        </li>
        <li className={strength.requirements.hasNumber ? 'text-green-600' : 'text-gray-500'}>
          {strength.requirements.hasNumber ? '✓' : '○'} One number
        </li>
        <li className={strength.requirements.hasSpecial ? 'text-green-600' : 'text-gray-500'}>
          {strength.requirements.hasSpecial ? '✓' : '○'} One special character
        </li>
      </ul>
    </div>
  );
};
```

### Usage in Registration Form

```typescript
// pages/Register.tsx
import { useState } from 'react';
import { PasswordStrengthIndicator, checkPasswordStrength } from './components/PasswordStrengthIndicator';

export const RegisterPage = () => {
  const [formData, setFormData] = useState({
    phone: '',
    password: '',
    name: '',
  });
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Check password strength before submitting
    const strength = checkPasswordStrength(formData.password);
    if (strength.score < 5) {
      setError('Please use a stronger password that meets all requirements');
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/users/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone: formData.phone,
          password: formData.password,
          name: formData.name,
          role: 'buyer',
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        // Handle validation errors from backend
        if (data.detail && Array.isArray(data.detail)) {
          setError(data.detail[0].msg);
        } else {
          setError('Registration failed');
        }
        return;
      }

      // Success - redirect to login or auto-login
      window.location.href = '/login?registered=true';
    } catch (err) {
      setError('Network error. Please try again.');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="phone">Phone Number</label>
        <input
          id="phone"
          type="tel"
          value={formData.phone}
          onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
          placeholder="+998901234567"
          required
        />
      </div>

      <div>
        <label htmlFor="name">Full Name</label>
        <input
          id="name"
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="John Doe"
        />
      </div>

      <div>
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={formData.password}
          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          placeholder="Enter a strong password"
          required
        />
        <PasswordStrengthIndicator password={formData.password} />
      </div>

      {error && (
        <div className="text-red-600 text-sm">{error}</div>
      )}

      <button
        type="submit"
        className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
      >
        Register
      </button>
    </form>
  );
};
```

### Vanilla JavaScript Version

If you're not using React:

```html
<input type="password" id="password" />
<div id="password-strength"></div>

<script>
const passwordInput = document.getElementById('password');
const strengthDiv = document.getElementById('password-strength');

passwordInput.addEventListener('input', (e) => {
  const password = e.target.value;
  
  const requirements = {
    minLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
    hasSpecial: /[!@#$%^&*(),.?":{}|<>]/.test(password),
  };
  
  const score = Object.values(requirements).filter(Boolean).length;
  
  let html = '<ul>';
  html += `<li style="color: ${requirements.minLength ? 'green' : 'gray'}">
    ${requirements.minLength ? '✓' : '○'} At least 8 characters
  </li>`;
  html += `<li style="color: ${requirements.hasUppercase ? 'green' : 'gray'}">
    ${requirements.hasUppercase ? '✓' : '○'} One uppercase letter
  </li>`;
  html += `<li style="color: ${requirements.hasLowercase ? 'green' : 'gray'}">
    ${requirements.hasLowercase ? '✓' : '○'} One lowercase letter
  </li>`;
  html += `<li style="color: ${requirements.hasNumber ? 'green' : 'gray'}">
    ${requirements.hasNumber ? '✓' : '○'} One number
  </li>`;
  html += `<li style="color: ${requirements.hasSpecial ? 'green' : 'gray'}">
    ${requirements.hasSpecial ? '✓' : '○'} One special character
  </li>`;
  html += '</ul>';
  
  strengthDiv.innerHTML = html;
});
</script>
```

## Examples

### ✅ Strong Passwords
- `MyP@ssw0rd`
- `Secure#2024`
- `Admin@123!`
- `Test$Pass99`

### ❌ Weak Passwords (Will Be Rejected)
- `password` - No uppercase, no number, no special char
- `Password` - No number, no special char
- `Pass123` - Too short, no special char
- `PASSWORD123!` - No lowercase
- `password123!` - No uppercase

## Security Best Practices

1. **Never store plain text passwords** - Already handled by `passlib` bcrypt hashing
2. **Use HTTPS in production** - Encrypt password transmission
3. **Implement rate limiting** - Prevent brute force attacks
4. **Add password confirmation field** - Ensure user typed correctly
5. **Consider adding "Show Password" toggle** - Improve UX
6. **Implement "Forgot Password" flow** - For password recovery

## Additional Features to Consider

### Password Confirmation

```typescript
const [confirmPassword, setConfirmPassword] = useState('');

// In form validation
if (formData.password !== confirmPassword) {
  setError('Passwords do not match');
  return;
}
```

### Show/Hide Password Toggle

```typescript
const [showPassword, setShowPassword] = useState(false);

<input
  type={showPassword ? 'text' : 'password'}
  // ... other props
/>
<button onClick={() => setShowPassword(!showPassword)}>
  {showPassword ? 'Hide' : 'Show'}
</button>
```

### Password Generator

```typescript
const generateStrongPassword = (): string => {
  const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const lowercase = 'abcdefghijklmnopqrstuvwxyz';
  const numbers = '0123456789';
  const special = '!@#$%^&*(),.?":{}|<>';
  
  const all = uppercase + lowercase + numbers + special;
  
  let password = '';
  password += uppercase[Math.floor(Math.random() * uppercase.length)];
  password += lowercase[Math.floor(Math.random() * lowercase.length)];
  password += numbers[Math.floor(Math.random() * numbers.length)];
  password += special[Math.floor(Math.random() * special.length)];
  
  for (let i = 4; i < 12; i++) {
    password += all[Math.floor(Math.random() * all.length)];
  }
  
  return password.split('').sort(() => Math.random() - 0.5).join('');
};
```
