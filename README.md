# Dough Re Mi Patisserie (formerly JeCole's Bakery)

This repository contains the web application for Dough Re Mi Patisserie, an online artisanal bakery storefront. 
The application was migrated from a legacy PHP/MySQL architecture to a robust Python/Django framework to enhance security, scalability, and maintainability.

## Features
* Modern, responsive UI for browsing pastries and breads.
* User Authentication (Signup, Login, Logout) with secure password hashing.
* Interactive cart functionality.
* Checkout and Billing forms with server-side validation.
* Robust security measures including built-in CSRF protection, SQL Injection prevention via the Django ORM, and secure session management.

## Prerequisites
* Python 3.x
* Git

## Installation and Setup

1. **Clone the repository and switch to the Django branch:**
   ```bash
   git clone https://github.com/0910bayts/Dough-Re-Mi-Patisserie.git
   cd Dough-Re-Mi-Patisserie
   git checkout Django-Version
   ```

2. **Set up the virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Seed the database (Optional):**
   If you need to populate the initial bakery menu items, run the seed script:
   ```bash
   python seed.py
   ```

6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```
   Navigate to `http://127.0.0.1:8000/` in your web browser.

## Email Setup for Gmail
To send checkout receipts by email, configure Gmail SMTP in your `.env` file:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=yourgmailaddress@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=yourgmailaddress@gmail.com
```

If you use Gmail, generate an App Password from your Google account and use that as `EMAIL_HOST_PASSWORD`.

## Security Enhancements
By migrating to Django, this application implements strong security controls out-of-the-box:
- **Spoofing:** Prevented through Django's secure authentication system and automatic session ID regeneration.
- **Tampering:** Mitigated by the Django ORM (which automatically parameterizes queries against SQL Injection) and built-in CSRF Middleware for all POST forms.
- **Information Disclosure:** Handled via secure environment variable configurations (`.env`) and Django's debug-mode toggles preventing raw database errors in production.
