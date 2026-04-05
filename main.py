import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from routers import prices, images

load_dotenv()

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(title="CS2 Tracker API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
