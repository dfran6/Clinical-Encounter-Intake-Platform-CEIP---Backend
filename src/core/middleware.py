from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time
import logging

from src.core.utils import decode_token
from src.core.redis import token_in_blocklist

logger = logging.getLogger('puzzles_api.middleware')
logger.setLevel(logging.INFO)


def register_middleware(app: FastAPI):

    @app.middleware('http')
    async def custom_logging_and_user_attach(request: Request, call_next):
        start_time = time.time()

        request.state.user = None

        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

            token_data = decode_token(token)

            if token_data:
                try:
                    is_revoked = await token_in_blocklist(token_data["jti"])

                    if not is_revoked:
                        request.state.user = token_data.get("user")

                except Exception as e:
                    logger.error("Token validation error: %s", e)

        response = await call_next(request)

        processing_time = time.time() - start_time
        
        message = (
            f"{request.client.host}:{request.client.port} - "
            f"{request.method} - {request.url.path} - "
            f"{response.status_code} completed after {processing_time:.4f}s"
        )

        logger.info(message)
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "http://127.0.0.1:5173/"]
    )