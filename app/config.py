import os
import secrets

# Read from the environment. If unset, a random key is generated at startup,
# which is fine for local use (tokens become invalid when the app restarts).
SECRET_KEY: str = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
