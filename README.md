# AI Picture APIs

This is a FastAPI project with Supabase Authentication.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Configuration

The configuration is in `app/config.py`. It includes Supabase keys and other credentials.

## API Endpoints

- **Auth**
  - `POST /auth/signup`: Create a new account
  - `POST /auth/login`: Login (returns access token)
  - `POST /auth/logout`: Logout

- **Users**
  - `GET /users/me`: View current user profile (Requires Bearer Token)
  - `DELETE /users/me`: Delete current user account (Requires Bearer Token)

## Authentication

To access protected endpoints (`/users/me`), you must provide the access token obtained from `/auth/login` in the `Authorization` header:

```
Authorization: Bearer <your_access_token>
```
