import logging
import os
import threading
import time
import urllib.request

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import API_KEY, BASE_DIR, PING_EVERY, PING_URL
from middlewares import register_middlewares
from routes import router

app = FastAPI(title="Clinic booking API")


def err(status, message):
    return JSONResponse({"error": message}, status_code=status)


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, exc: RequestValidationError):
    return err(400, "invalid request")


@app.exception_handler(StarletteHTTPException)
async def on_http_error(request: Request, exc: StarletteHTTPException):
    return err(exc.status_code, str(exc.detail))


def keep_alive():
    while True:
        time.sleep(PING_EVERY)
        try:
            with urllib.request.urlopen(f"{PING_URL.rstrip('/')}/health", timeout=10) as response:
                response.read()
        except Exception:
            logging.getLogger(__name__).warning("Render keep-alive ping failed", exc_info=True)


@app.on_event("startup")
def start_keep_alive():
    if PING_URL:
        threading.Thread(target=keep_alive, daemon=True).start()


register_middlewares(app, API_KEY)
app.include_router(router)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
