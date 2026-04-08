from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.admin import router as admin_router
from routes.ask import router as ask_router
from routes.upload import router as upload_router

app = FastAPI(title="Chat with PDF API", version="1.0.0")

# Allow the React frontend to call this API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


app.include_router(upload_router, prefix="", tags=["upload"])
app.include_router(ask_router, prefix="", tags=["chat"])
app.include_router(admin_router, prefix="", tags=["admin"])
