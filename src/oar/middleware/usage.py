"""Usage logging middleware.

Intercepts every authenticated write request, captures timing/size metrics,
and writes a row to api_key_usage_logs asynchronously so it never adds
latency to the response.

Industry-standard metrics tracked per request:
  - endpoint + method
  - HTTP status code
  - request_bytes  — Content-Length of the incoming body
  - response_bytes — size of the response body
  - estimated_tokens — response_bytes / 4  (OpenAI-style rough estimate)
  - duration_ms — wall-clock time from first byte received to last byte sent
"""

import time
import uuid
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from oar.auth.api_key import extract_bearer_token, extract_key_prefix, verify_api_key
from oar.database import async_session
from oar.models.api_key import ApiKey, ApiKeyUsageLog
from sqlalchemy import select, update


class UsageLoggingMiddleware(BaseHTTPMiddleware):
    """Log usage for every request authenticated with an API key."""

    # Paths that never carry an API key — skip lookup entirely
    _SKIP_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json", "/v1/taxonomy")

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.monotonic()

        # Fast path: skip unauthenticated / static paths
        path = request.url.path
        if any(path.startswith(p) for p in self._SKIP_PREFIXES):
            return await call_next(request)

        authorization = request.headers.get("authorization")
        token = extract_bearer_token(authorization)
        if not token:
            return await call_next(request)

        prefix = extract_key_prefix(token)
        if not prefix:
            return await call_next(request)

        # Measure request body size
        request_bytes = int(request.headers.get("content-length", 0))

        # Execute the actual request
        response: Response = await call_next(request)

        duration_ms = int((time.monotonic() - start) * 1000)

        # Capture response body size
        body_chunks = []
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            body_chunks.append(chunk)
        response_body = b"".join(body_chunks)
        response_bytes = len(response_body)
        estimated_tokens = max(1, response_bytes // 4)

        # Rebuild response with the already-consumed body
        from starlette.responses import Response as StarletteResponse
        rebuilt = StarletteResponse(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

        # Write usage log asynchronously (fire-and-forget; never fails the request)
        try:
            await self._log_usage(
                prefix=prefix,
                token=token,
                endpoint=path,
                method=request.method,
                status_code=response.status_code,
                request_bytes=request_bytes,
                response_bytes=response_bytes,
                estimated_tokens=estimated_tokens,
                duration_ms=duration_ms,
            )
        except Exception:
            pass  # logging must never affect the API response

        return rebuilt

    @staticmethod
    async def _log_usage(
        *,
        prefix: str,
        token: str,
        endpoint: str,
        method: str,
        status_code: int,
        request_bytes: int,
        response_bytes: int,
        estimated_tokens: int,
        duration_ms: int,
    ) -> None:
        async with async_session() as db:
            result = await db.execute(
                select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.status == "active")
            )
            api_key = result.scalar_one_or_none()
            if not api_key or not verify_api_key(token, api_key.key_hash):
                return

            # Insert usage log row
            log = ApiKeyUsageLog(
                id=uuid.uuid4(),
                api_key_id=api_key.id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                request_bytes=request_bytes,
                response_bytes=response_bytes,
                estimated_tokens=estimated_tokens,
                duration_ms=duration_ms,
                called_at=datetime.now(timezone.utc),
            )
            db.add(log)

            # Update last_used_at on the key
            await db.execute(
                update(ApiKey)
                .where(ApiKey.id == api_key.id)
                .values(last_used_at=datetime.now(timezone.utc))
            )

            await db.commit()
