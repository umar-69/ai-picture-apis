# AI Picture APIs

This is a FastAPI project with Supabase Authentication and Storage.

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

The configuration is in `app/config.py`. It uses environment variables from `.env`.

## API Endpoints

- **Auth**
  - `POST /auth/signup`: Create a new account
  - `POST /auth/login`: Login (returns access token)
  - `POST /auth/logout`: Logout

- **Users**
  - `GET /users/me`: View current user profile (Requires Bearer Token)
  - `DELETE /users/me`: Delete current user account (Requires Bearer Token)

- **Storage**
  - `POST /storage/upload`: Upload file (Requires Bearer Token)
  - `GET /storage/list`: List user's files (Requires Bearer Token)

## Authentication

To access protected endpoints (`/users/me`, `/storage/upload`), you must provide the access token obtained from `/auth/login` in the `Authorization` header:

```
Authorization: Bearer <your_access_token>
```

## Deployment to Render

1. Create a new Web Service on Render.
2. Connect your GitHub repository.
3. Set the Build Command: `pip install -r requirements.txt`
4. Set the Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add Environment Variables in Render Dashboard (copy from `.env`).
