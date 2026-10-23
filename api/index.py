import os
import sys
import json
import traceback

# Zero non-standard-library imports at module load time!
# This guarantees Vercel's Python runtime will NEVER crash with FUNCTION_INVOCATION_FAILED.

_api_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.abspath(os.path.join(_api_dir, ".."))
_candidate_dirs = [
    _root_dir,
    os.path.join(_root_dir, "backend"),
    _api_dir,
    os.path.join(_api_dir, "backend"),
    os.getcwd(),
    os.path.join(os.getcwd(), "backend"),
    "/var/task",
    "/var/task/backend",
]
for p in _candidate_dirs:
    if p and os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

_backend_app = None
_init_error = None

def get_backend_app():
    global _backend_app, _init_error
    if _backend_app is not None:
        return _backend_app
    if _init_error is not None:
        return None
    try:
        from fastapi import FastAPI
        from fastapi.staticfiles import StaticFiles
        from backend.main import app as core_app
        
        gateway = FastAPI(title="Veriflow Gateway")
        gateway.mount("/api", core_app)
        
        # Mount dist if present
        dist_dir = None
        for candidate_dist in [
            os.path.join(_root_dir, "frontend", "dist"),
            os.path.join(_api_dir, "frontend", "dist"),
            os.path.join(os.getcwd(), "frontend", "dist"),
            os.path.join(_root_dir, "dist"),
        ]:
            if os.path.isdir(candidate_dist):
                dist_dir = candidate_dist
                break
                
        if dist_dir:
            assets_dir = os.path.join(dist_dir, "assets")
            if os.path.isdir(assets_dir):
                gateway.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
                
        _backend_app = gateway
        return _backend_app
    except Exception as e:
        _init_error = traceback.format_exc()
        return None

async def send_json(send, status_code: int, data: dict):
    body = json.dumps(data, indent=2).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status_code,
        "headers": [
            [b"content-type", b"application/json"],
            [b"content-length", str(len(body)).encode("utf-8")],
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })

async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    if scope["type"] != "http":
        return

    path = scope.get("path", "/")

    # Health check endpoint
    if path == "/api/health":
        backend = get_backend_app()
        if backend is None:
            await send_json(send, 500, {
                "status": "error",
                "message": "Backend initialization failed",
                "python_version": sys.version,
                "error": _init_error,
                "sys_path": sys.path,
                "cwd": os.getcwd(),
            })
            return
        await send_json(send, 200, {
            "status": "ok",
            "service": "veriflow-backend",
            "python_version": sys.version,
        })
        return

    # Check backend app
    backend = get_backend_app()
    if backend is None:
        await send_json(send, 500, {
            "status": "error",
            "message": "Backend initialization failed",
            "python_version": sys.version,
            "error": _init_error,
            "sys_path": sys.path,
            "cwd": os.getcwd(),
        })
        return

    # Forward request to FastAPI gateway
    await backend(scope, receive, send)
