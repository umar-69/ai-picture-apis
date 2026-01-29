from fastapi import FastAPI
from app.routers import auth, users

app = FastAPI(title="AI Picture APIs")

app.include_router(auth.router)
app.include_router(users.router)

@app.get("/")
def root():
    return {"message": "Welcome to AI Picture APIs"}
