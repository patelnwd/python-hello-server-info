import os
import socket
import platform
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, Response

app = FastAPI()


def get_server_info(request: Request):
    hostname = socket.gethostname()

    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = None

    return {
        "hostname": hostname,
        "containerId": os.environ.get("HOSTNAME"),
        "ipAddress": ip,
        "platform": platform.platform(),
        "pythonVersion": platform.python_version(),
        "processId": os.getpid(),
        "serverTimeUtc": datetime.now(timezone.utc).isoformat(),
        "clientHost": request.client.host if request.client else None,
        "headers": {
            "host": request.headers.get("host"),
            "xForwardedFor": request.headers.get("x-forwarded-for"),
            "xForwardedProto": request.headers.get("x-forwarded-proto"),
            "xForwardedPort": request.headers.get("x-forwarded-port"),
        },
    }


def build_response(method: str, request: Request, include_server: bool):
    data = {
        "message": "Hello World",
        "method": method,
    }

    if include_server:
        data["serverInfo"] = get_server_info(request)

    return data


@app.api_route(
    "/",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "TRACE", "HEAD"],
)
async def root(request: Request, serverInfo: bool = Query(False)):
    method = request.method

    if method == "HEAD":
        headers = {}
        if serverInfo:
            info = get_server_info(request)
            headers = {
                "X-Hostname": str(info["hostname"]),
                "X-Container": str(info["containerId"]),
                "X-PID": str(info["processId"]),
            }
        return Response(status_code=200, headers=headers)

    return JSONResponse(content=build_response(method, request, serverInfo))


@app.get("/health")
async def health(request: Request, serverInfo: bool = Query(False)):
    data = {"status": "healthy"}

    if serverInfo:
        data["serverInfo"] = get_server_info(request)

    return data