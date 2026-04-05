import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import prices, images

load_dotenv()

app = FastAPI(title="CS2 Tracker API", version="1.0.0")

allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins_raw.strip() == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in allowed_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(prices.router, prefix="/api")
app.include_router(images.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
