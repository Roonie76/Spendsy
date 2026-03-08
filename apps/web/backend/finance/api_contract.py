from __future__ import annotations

import uuid

from rest_framework.response import Response


def request_id_from_request(request) -> str:
    header_id = (request.headers.get("X-Request-ID") or "").strip()
    return header_id or str(uuid.uuid4())


def success_response(request, data, message: str = "OK", code: str = "OK", http_status: int = 200):
    return Response(
        {
            "ok": True,
            "code": code,
            "message": message,
            "data": data,
            "meta": {"request_id": request_id_from_request(request)},
        },
        status=http_status,
    )


def error_response(request, message: str, code: str, http_status: int = 400, details=None):
    payload = {
        "ok": False,
        "code": code,
        "message": message,
        "meta": {"request_id": request_id_from_request(request)},
    }
    if details is not None:
        payload["details"] = details
    return Response(payload, status=http_status)
