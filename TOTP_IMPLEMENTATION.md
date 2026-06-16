# Admin TOTP (Time-based One-Time Password) Implementation

## Overview
TOTP has been successfully implemented for the Django admin panel with enforced verification at login. This adds a security layer that requires admin/superuser accounts to verify using an authenticator app (Google Authenticator, Microsoft Authenticator, Authy, etc.).

## Components Created

### 1. **Database Model** (`bakery/models.py`)
- `TOTPSecret` model stores:
  - User reference (OneToOne)
  - TOTP secret key (unique)
  - Verification status
  - Creation timestamp
  - Backup codes (for future use)

### 2. **Custom Admin Site** (`bakery/admin.py`)
- `TOTPAdminSite` class overrides Django's default AdminSite
- Overrides `login()` method to intercept admin login
- Checks if user is superuser/admin/staff
- If TOTP is enabled, redirects to TOTP verification
- If TOTP is not set up, allows login (optional setup)

### 3. **Views** (`bakery/views.py`)
- `admin_totp_setup()`: Admin page to set up TOTP
  - Generates QR code for scanning
  - Shows secret key for manual entry
  - Verifies setup code before enabling
  
- `admin_totp_disable()`: Admin page to disable TOTP
  - Requires confirmation
  
- `verify_admin_totp()`: TOTP verification during admin login
  - Rate limiting (5 failed attempts)
  - Session validation
  - Sets `admin_totp_verified` in session after successful verification

### 4. **Middleware** (`bakery/middleware.py`)
- `AdminTOTPMiddleware`: 
  - Provides secondary check for already-authenticated admin users
  - Redirects to TOTP verification if not verified in current session
  - Allows admin to verify if TOTP is enabled

### 5. **URL Routes** (`bakery/urls.py`)
```
/admin/totp/setup/      - Setup TOTP for authenticated admin
/admin/totp/disable/    - Disable TOTP for authenticated admin
/admin/totp/verify/     - Verify TOTP code during login
```

### 6. **Templates**
- `admin/totp_setup.html`: Setup interface with QR code display
- `admin/verify_totp.html`: TOTP verification form during login
- `admin/totp_disable_confirm.html`: Confirmation page to disable TOTP

### 7. **Admin Registration**
- `TOTPSecret` model registered in Django admin panel
- Can view/manage TOTP secrets from admin
- Custom AdminSite applied globally to all admin pages

## How It Works

### Setup Flow
1. Admin navigates to `/admin/totp/setup/` (after logging in)
2. System generates a new TOTP secret (if not exists)
3. QR code and secret key are displayed
4. Admin scans QR code or enters secret in authenticator app
5. Admin enters 6-digit code from authenticator
6. System verifies the code using `pyotp.TOTP`
7. If valid, TOTP is enabled and stored in database

### Login Flow (Primary)
1. Admin goes to `/admin/` and enters username/password
2. Custom `TOTPAdminSite.login()` method intercepts authentication
3. Credentials are verified using Django's authentication
4. If user is superuser/admin/staff **and** has TOTP enabled:
   - Redirects to `/admin/totp/verify/` for TOTP verification
   - Stores user ID in session
5. Admin enters 6-digit code from authenticator app
6. System verifies code with rate limiting (5 attempts max)
7. If valid, logs user in and sets `admin_totp_verified` session flag

### Security Features
- ✅ Time-based OTP (valid for 30-second windows)
- ✅ Rate limiting on verification attempts (5 max)
- ✅ Session-based verification state
- ✅ Audit logging of TOTP operations
- ✅ Support for standard authenticator apps
- ✅ Can be disabled by admin if needed
- ✅ Enforced at login stage (not just on page access)

## Dependencies Added
- `pyotp~=2.9` - TOTP implementation
- `qrcode~=8.0` - QR code generation

## Database
- New migration: `bakery/migrations/0017_add_totp_secret.py`
- Creates `bakery_totpsecret` table

## Key Differences from Login MFA
| Feature | Login MFA | Admin TOTP |
|---------|-----------|-----------|
| Method | Email-based 6-digit code | Time-based OTP |
| Duration | 2 minutes expiration | 30-second time window |
| Optional | Yes (can be toggled) | Yes (can be disabled) |
| Affected Users | All users | Admin/Superuser only |
| Protection | Login security | Admin panel access |
| Enforcement Point | During login form | During login POST (custom AdminSite) |

## Usage

### For First-Time Admin Login
1. Admin logs in with username/password at `/admin/`
2. If TOTP is not set up, login proceeds normally
3. Admin should navigate to `/admin/totp/setup/` to enable TOTP

### For Admins with TOTP Enabled
1. Admin goes to `/admin/`
2. Enters username and password
3. Gets redirected to `/admin/totp/verify/`
4. Enters 6-digit code from authenticator app
5. Admin panel access is granted

### To Disable TOTP
1. Log in to admin panel (with TOTP if enabled)
2. Navigate to `/admin/totp/disable/`
3. Confirm the action
4. TOTP is removed

### To Re-Enable or Change Authenticator
1. First disable TOTP (if already enabled)
2. Navigate to `/admin/totp/setup/`
3. Scan new QR code with authenticator app
4. Verify with new 6-digit code

## Session Management
- `totp_user_id`: Temporarily stores user ID during TOTP verification
- `totp_pending_username`: Stores username for verification context
- `admin_totp_verified`: Set to `True` after successful verification
- Clears verification state on logout

## Logging
All TOTP operations are logged with:
- User email
- IP address
- Success/failure status
- Attempt counts
- Timestamps

## Troubleshooting

**Issue**: Admin can still log in without TOTP
- **Solution**: Make sure you're using the custom admin site. Check that the TOTP is actually enabled for the user in the database.

**Issue**: TOTP code not working
- **Solution**: Ensure device time is synchronized. Authenticator apps require accurate system time.

**Issue**: Lost authenticator app
- **Solution**: Contact system administrator to disable TOTP from the database for that user via management command or SQL.

