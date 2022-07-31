# Standard Library
import base64
import json
import os
from functools import lru_cache
from typing import Optional

# Third Party
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import httpx
from passlib.context import CryptContext

load_dotenv()

basic_scheme = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
COGNITO_HOST = os.getenv("COGNITO_HOST")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
COGNITO_REDIRECT_URI = os.getenv("COGNITO_REDIRECT_URI")


def verify_password(plain_password, hashed_password):
    """Verify provided password against the retrieved hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Generate a hash of password."""
    return pwd_context.hash(password)


def redirect_to_login(referer_url="/"):
    """Return a Response to Redirect to Login URI."""
    SCOPES = ["email", "aws.cognito.signin.user.admin", "openid"]
    parameters = {
        "client_id": COGNITO_CLIENT_ID,
        "response_type": "code",
        "scope": "+".join(SCOPES),
        "redirect_uri": COGNITO_REDIRECT_URI,
    }
    query_params = "&".join([f"{k}={v}" for k, v in parameters.items()])
    LOGIN_URI = f"{COGNITO_HOST}/login?{query_params}"

    response = RedirectResponse(LOGIN_URI)
    response.set_cookie(key="redirect_post_login", value=referer_url)
    return response


async def exchange_oauth2_code(code):
    """Exchange authorization code for OAuth2 token.

    https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html
    """
    token = None
    URI = f"{COGNITO_HOST}/oauth2/token"
    basic_auth = base64.b64encode(f"{COGNITO_CLIENT_ID}:{COGNITO_CLIENT_SECRET}".encode("ascii")).decode()
    headers = {"Authorization": f"Basic {basic_auth}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "client_id": COGNITO_CLIENT_ID,
        "code": code,
        "redirect_uri": COGNITO_REDIRECT_URI,
    }
    async with httpx.AsyncClient() as client:
        token = await client.post(URI, headers=headers, data=data)
        token = token.json()
    return token


def handle_auth_redirect(request: Request, response: Response, token: str):
    referer_url = request.cookies.get("redirect_post_login", "/")
    referer_url = referer_url if referer_url else "/"
    response.set_cookie(key="bearer-token", value=token)
    response.set_cookie(key="redirect_post_login", value="")
    response.status_code = 307
    response.headers["location"] = referer_url
    return response
