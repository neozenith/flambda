# Third Party
from fastapi import Request, Response
from fastapi.responses import RedirectResponse

from .cognito import authenticated_jwt, get_login_uri


def authenticate_request(request, JWKS):
    print(f"authenticate_request#0 {request.url=}")

    id_token = request.cookies.get("id_token", None)
    access_token = request.cookies.get("access_token", None)
    refresh_token = request.cookies.get("refresh_token", None)

    print(f"authenticate_request#1 {id_token=}")
    if not id_token:
        return False

    id_authenticated_claims = authenticated_jwt(token=id_token, keys=JWKS)
    access_authenticated_claims = authenticated_jwt(token=access_token, keys=JWKS)

    print(f"authenticate_request#3 {id_authenticated_claims=}")
    print(f"authenticate_request#3 {access_authenticated_claims=}")

    return {"id": id_authenticated_claims, "access": access_authenticated_claims}


def redirect_to_login(request):
    """Return a Response to Redirect to Login URI."""
    response = RedirectResponse(get_login_uri())
    # Only set a new redirect post login if it is not already set
    if not request.cookies.get("redirect_post_login", None):
        response.set_cookie(key="redirect_post_login", value=request.url)
    return response


def handle_auth_redirect(request: Request, response: Response, token: str):
    """Redirect to original request if a token is provided.

    Also set the tokens as a cookie
    """
    if not token:
        return response

    referer_url = request.cookies.get("redirect_post_login", "/")
    referer_url = referer_url if referer_url else "/"

    response.status_code = 307
    response.headers["location"] = referer_url
    response.delete_cookie(key="redirect_post_login")
    response.set_cookie(key="id_token", value=token["id_token"], secure=True, httponly=True)
    response.set_cookie(key="access_token", value=token["access_token"], secure=True, httponly=True)
    response.set_cookie(key="refresh_token", value=token["refresh_token"], secure=True, httponly=True)

    return response


def handle_logout(response: Request):
    response.delete_cookie(key="id_token")
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    response.delete_cookie(key="redirect_post_login")
    response.status_code = 307
    response.headers["location"] = "/"
    return response
