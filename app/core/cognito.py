# Standard Library
import base64
import os
import time
from pprint import pprint as pp

# Third Party
import httpx
from dotenv import load_dotenv
from jose import jwk, jwt
from jose.utils import base64url_decode

load_dotenv()

COGNITO_HOST = os.getenv("COGNITO_HOST")
AWS_REGION = os.getenv("AWS_REGION")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
COGNITO_USERPOOL_ID = os.getenv("COGNITO_USERPOOL_ID")
COGNITO_REDIRECT_URI = os.getenv("COGNITO_REDIRECT_URI")


def get_login_uri():
    SCOPES = ["email", "aws.cognito.signin.user.admin", "openid"]
    parameters = {
        "client_id": COGNITO_CLIENT_ID,
        "response_type": "code",
        "scope": "+".join(SCOPES),
        "redirect_uri": COGNITO_REDIRECT_URI,
    }
    query_params = "&".join([f"{k}={v}" for k, v in parameters.items()])
    LOGIN_URI = f"{COGNITO_HOST}/login?{query_params}"
    return LOGIN_URI


def get_jwks(userpool_id, region):
    keys_url = f"https://cognito-idp.{region}.amazonaws.com/{userpool_id}/.well-known/jwks.json"
    print(f"{keys_url=}")
    with httpx.Client() as client:
        keys = client.get(keys_url).json()["keys"]
        
    return keys


def authenticated_jwt(token, keys):
    if not token:
        return False
    
    headers = jwt.get_unverified_headers(token)

    # search for the kid in the downloaded public keys
    K = [k for k in keys if k["kid"] == headers["kid"]]
    if not K:  # If empty list of matches
        print("Public key not found in jwks.json")
        return False
    
    public_key = jwk.construct(K[0])
    message, encoded_signature = str(token).rsplit(".", 1)
    decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))
    
    # verify the signature
    if not public_key.verify(message.encode("utf8"), decoded_signature):
        print("Signature verification failed")
        return False

    print("Signature successfully verified")
    
    claims = jwt.get_unverified_claims(token)
    pp(claims)
    
    if time.time() > claims["exp"]:
        print("Token is expired")
        return False

    # (use claims['client_id'] if verifying an access token)
    if "aud" in claims and claims["aud"] != COGNITO_CLIENT_ID:
        print("Token was not issued for this audience")
        return False

    return claims


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
