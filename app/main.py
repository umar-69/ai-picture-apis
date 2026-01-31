from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, users, storage, business, ai

app = FastAPI(title="AI Picture APIs")

# Configure CORS
# Explicitly allow OPTIONS and all methods/headers to fix 405 errors and pre-flight issues
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now (development)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods including OPTIONS
    allow_headers=["*"],  # Allows all headers
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(storage.router)
app.include_router(business.router)
app.include_router(ai.router)

@app.get("/")
def root():
    return {"message": "Welcome to AI Picture APIs"}
