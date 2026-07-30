import logging
import os

from fastapi import FastAPI , Request
from fastapi.middleware.cors import CORSMiddleware
from controller import user_controller, expense_controller
from database import engine, Base
import auth
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# One place that configures logging for the whole app - every module below
# just does `logging.getLogger("expense_tracker.<name>")` and inherits this.
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("expense_tracker.main")

from oauth.router import router as oauth_router
from mcp_server import build_mcp_asgi_app
from authz import client as authz_client
from authz import service as authz_service
from models.user_model import User
import mock_idp
from oauth import service as oauth_service
from oauth.models import TrustedIssuer
from database import SessionLocal

# Import so their SQLAlchemy models register on Base before create_all runs.
import oauth.models  # noqa: F401

# Create database tables
Base.metadata.create_all(bind=engine)

# Idempotent: finds-or-creates the OpenFGA store/model. Safe to call on
# every startup, including against data left over from a previous run.
authz_client.bootstrap()
logger.info("OpenFGA store/model bootstrapped")

# Optional one-time bootstrap for the very first admin: there's no other way
# to become admin, since granting admin requires already being one. Set
# INITIAL_ADMIN_USERNAMES=alice,bob in the environment to promote existing
# users on startup - a no-op for usernames that don't exist yet or are
# already admins.
for _username in filter(None, os.environ.get("INITIAL_ADMIN_USERNAMES", "").split(",")):
    _user = next((u for u in User.get_users() if u.username == _username.strip()), None)
    if _user:
        authz_service.grant_admin(_user.id)
        logger.info("granted admin to %s (id=%s) via INITIAL_ADMIN_USERNAMES", _user.username, _user.id)

# Bootstrap the mock IdP (mock_idp.py) as a default trusted issuer, purely
# so Cross-App Access is testable out of the box. In a real deployment,
# replace this with a TrustedIssuer row pointing at your actual external
# IdP, and don't run mock_idp.py at all.
with SessionLocal() as _db:
    _mock_issuer = mock_idp.issuer_url(oauth_service.ISSUER)
    if not _db.query(TrustedIssuer).filter(TrustedIssuer.issuer == _mock_issuer).first():
        _db.add(TrustedIssuer(
            issuer=_mock_issuer,
            jwks_url=f"{_mock_issuer}/.well-known/jwks.json",
            subject_claim="preferred_username",
        ))
        _db.commit()

# Built before the FastAPI app so its lifespan (needed by FastMCP's session
# manager) can be passed in at construction time.
mcp_app = build_mcp_asgi_app()

# FastAPI instance
app = FastAPI(lifespan=mcp_app.lifespan)

# Bearer-token auth only (no cookies), so allow_credentials stays False -
# there's nothing cross-site cookie auth could leak.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",") if o],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Mock external IdP for demonstrating Cross-App Access - see mock_idp.py's
# module docstring. Not something a real deployment would run.
app.include_router(mock_idp.router, prefix="/mock-idp", tags=["mock-idp (demo only)"])

# MCP server (protected resource). mcp_app itself already lays out the /mcp
# endpoint plus its own RFC 9728 metadata routes (see mcp_server.py), so it's
# mounted at root, not under an extra /mcp prefix. This must be the LAST
# route registered: Starlette tries routes in registration order, so the
# explicit routes/routers above still win over this catch-most mount.
app.mount("/", mcp_app)