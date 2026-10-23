import os
import sys
import traceback
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Diagnostic tracking
init_error = None
debug_context = {}

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    task_dir = "/var/task"
    task_backend = "/var/task/backend"
    
    candidate_paths = [
        current_dir,
        parent_dir,
        os.path.join(current_dir, "backend"),
        os.path.join(parent_dir, "backend"),
        task_dir,
        task_backend,
        os.getcwd(),
        os.path.join(os.getcwd(), "backend"),
    ]
    
    for p in candidate_paths:
        if p and os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)

    debug_context["sys_path"] = list(sys.path)
    debug_context["cwd"] = os.getcwd()
    debug_context["current_dir"] = current_dir
    debug_context["current_dir_files"] = os.listdir(current_dir) if os.path.exists(current_dir) else []
    debug_context["parent_dir_files"] = os.listdir(parent_dir) if os.path.exists(parent_dir) else []
    if os.path.exists(task_dir):
        try:
            debug_context["task_dir_files"] = os.listdir(task_dir)
        except Exception:
            pass

    from backend.main import app as backend_app
except Exception as e:
    init_error = traceback.format_exc()
    backend_app = None

app = FastAPI(title="Veriflow Gateway")

@app.get("/api/health")
def api_health():
    if init_error:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": init_error, "debug": debug_context}
        )
    return {"status": "ok", "service": "veriflow-backend"}

@app.get("/api/debug")
def api_debug():
    return {
        "status": "error" if init_error else "ok",
        "init_error": init_error,
        "debug": debug_context
    }

if backend_app:
    # Mount backend app under /api for vercel rewrites and under / for root requests
    app.mount("/api", backend_app)
    app.mount("/", backend_app)
else:
    @app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"])
    def catch_all_api(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "backend_initialization_failed",
                "error": init_error,
                "debug": debug_context
            }
        )
