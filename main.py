from fastapi import FastAPI , Request
from controller import user_controller, expense_controller
from database import engine, Base
import auth
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

from oauth.router import router as oauth_router
from mcp_server import build_mcp_asgi_app

# Import so their SQLAlchemy models register on Base before create_all runs.
import oauth.models  # noqa: F401

# Create database tables
Base.metadata.create_all(bind=engine)

# Built before the FastAPI app so its lifespan (needed by FastMCP's session
# manager) can be passed in at construction time.
mcp_app = build_mcp_asgi_app()

# FastAPI instance
app = FastAPI(lifespan=mcp_app.lifespan)

# Set the correct template directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(request, "home.html", {})



# Include controllers
app.include_router(user_controller.router, prefix="/users", tags=["Users"])
app.include_router(expense_controller.router, prefix="/expenses", tags=["Expenses"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])

# OAuth 2.1 authorization server (DCR + CIMD + metadata) lives at root because
# /.well-known/* paths are fixed by spec and can't sit under a prefix.
app.include_router(oauth_router, tags=["oauth"])

# MCP server (protected resource). mcp_app itself already lays out the /mcp
# endpoint plus its own RFC 9728 metadata routes (see mcp_server.py), so it's
# mounted at root, not under an extra /mcp prefix. This must be the LAST
# route registered: Starlette tries routes in registration order, so the
# explicit routes/routers above still win over this catch-most mount.
app.mount("/", mcp_app)