from __future__ import annotations

import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def request_id_from_request(request: Request) -> str:
    header_id = (request.headers.get("X-Request-ID") or "").strip()
    return header_id or str(uuid.uuid4())


def success_response(request: Request, data, message: str = "OK", code: str = "OK", http_status: int = 200):
    payload = {
        "ok": True,
        "code": code,
        "message": message,
        "data": jsonable_encoder(data),
        "meta": {"request_id": request_id_from_request(request)},
    }
    return JSONResponse(payload, status_code=http_status)


def error_response(request: Request, message: str, code: str, http_status: int = 400, details=None):
    payload = {
        "ok": False,
        "code": code,
        "message": message,
        "meta": {"request_id": request_id_from_request(request)},
    }
    if details is not None:
        payload["details"] = details
    return JSONResponse(jsonable_encoder(payload), status_code=http_status)
