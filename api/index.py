import os
import sys
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Setup paths
api_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(api_dir, ".."))
candidate_dirs = [
    root_dir,
    os.path.join(root_dir, "backend"),
    api_dir,
    os.path.join(api_dir, "backend"),
    os.getcwd(),
    os.path.join(os.getcwd(), "backend"),
    "/var/task",
    "/var/task/backend",
]
for p in candidate_dirs:
    if p and os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

# Import backend application
init_error = None
debug_context = {
    "api_dir": api_dir,
    "root_dir": root_dir,
    "cwd": os.getcwd(),
    "sys_path": list(sys.path),
}

try:
    from backend.main import app as backend_app
except Exception as e:
    init_error = traceback.format_exc()
    backend_app = None

app = FastAPI(title="Veriflow Fullstack Gateway")

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
    # Mount backend API endpoints under /api
    app.mount("/api", backend_app)
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

# Determine frontend distribution directory
dist_dir = None
for candidate_dist in [
    os.path.join(root_dir, "frontend", "dist"),
    os.path.join(api_dir, "frontend", "dist"),
    os.path.join(os.getcwd(), "frontend", "dist"),
    os.path.join(root_dir, "dist"),
    os.path.join(os.getcwd(), "dist"),
]:
    if os.path.isdir(candidate_dist):
        dist_dir = candidate_dist
        break

# Mount static assets if present
if dist_dir:
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# SPA catch-all handler for / and client routes
@app.get("/")
@app.get("/{full_path:path}")
def serve_spa(request: Request, full_path: str = ""):
    # If route starts with api/, return 404 for unhandled api endpoints
    if full_path.startswith("api/") or full_path == "api":
        return JSONResponse(status_code=404, content={"detail": "API route not found"})
    
    if dist_dir and os.path.isdir(dist_dir):
        # Check if requesting a direct static file in dist
        candidate_file = os.path.join(dist_dir, full_path)
        if full_path and os.path.isfile(candidate_file):
            return FileResponse(candidate_file)
        
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
            
    return HTMLResponse(
        content="""<!DOCTYPE html>
<html>
<head><title>Veriflow System</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 40px;">
  <h2>Veriflow Fullstack Serverless Gateway</h2>
  <p>Backend API is active at <a href="/api/health">/api/health</a>.</p>
</body>
</html>""",
        status_code=200
    )
