# Standard Library
import json
import os
from functools import lru_cache
from typing import Optional

# Third Party
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext

load_dotenv()

basic_scheme = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@lru_cache
def authorised_users():
    """Get a dictionary of authorised usernames and their bcrypted password hashes from env vars.

    NOTE: This is sketchy security practices purely for the sake of prototyping.
    """
    return json.loads(os.getenv("AUTHORISED_USERS", "{}"))


def get_user(username: str) -> Optional[str]:
    """Load User model from Database given a username."""
    return authorised_users().get(username, None)


def verify_password(plain_password, hashed_password):
    """Verify provided password against the retrieved hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Generate a hash of password."""
    return pwd_context.hash(password)


def authenticate_user(credentials: HTTPBasicCredentials = Depends(basic_scheme)):
    """Verify the username/password combination."""
    hashed_password = get_user(credentials.username)
    if not hashed_password or not verify_password(credentials.password, hashed_password):
        #  raise HTTPException(
        #      status_code=status.HTTP_401_UNAUTHORIZED,
        #      detail="Incorrect username or password",
        #      headers={"WWW-Authenticate": "Basic"},
        #  )
        return RedirectResponse("/docs")
    return True
