"""Bridges this app's two credential types into FastMCP's auth layer.

FastMCP's RemoteAuthProvider expects a single TokenVerifier. We accept two
different kinds of bearer credential on the same MCP endpoint:
  - OAuth 2.1 access tokens issued by oauth/router.py (RS256 JWTs, short-lived)
  - Static API keys issued via POST /auth/api-keys (long-lived, for scripts)
Both are exchanged the same way (an `Authorization: Bearer <token>` header),
so a single verifier that branches on the token's shape is the natural fit.
"""

from fastmcp.server.auth.auth import AccessToken, TokenVerifier

from oauth import service


class HybridTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        if token.startswith(service.API_KEY_PREFIX):
            info = service.verify_api_key(token)
            if not info:
                return None
            return AccessToken(
                token=token,
                client_id="api-key",
                scopes=["expenses:read", "expenses:write"],
                subject=str(info["user_id"]),
                claims={"sub": str(info["user_id"]), "username": ""},
            )

        try:
            claims = service.decode_access_token(token, expected_resource=service.MCP_RESOURCE_URL)
        except Exception:
            return None

        return AccessToken(
            token=token,
            client_id=claims.get("client_id", ""),
            scopes=(claims.get("scope") or "").split(),
            expires_at=claims.get("exp"),
            resource=claims.get("aud"),
            subject=claims.get("sub"),
            claims=claims,
        )
