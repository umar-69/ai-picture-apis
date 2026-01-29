from fastapi import FastAPI
from app.routers import auth, users, storage, business, ai

app = FastAPI(title="AI Picture APIs")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(storage.router)
app.include_router(business.router)
app.include_router(ai.router)

@app.get("/")
def root():
    return {"message": "Welcome to AI Picture APIs"}
