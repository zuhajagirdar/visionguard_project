import os
import sys

# Ensure root directory and backend directory are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_dir = os.path.join(root_dir, "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from fastapi import FastAPI
from backend.main import app as backend_app

app = FastAPI(title="Veriflow Serverless Gateway")

# Mount backend_app under /api for Vercel rewrites and root / for direct routing
app.mount("/api", backend_app)
app.mount("/", backend_app)
