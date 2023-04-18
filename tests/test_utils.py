from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from executor.http.server.routers.proxy import remove_prefix
from executor.http.server.utils.oauth2cookie import OAuth2PasswordBearerCookie


def test_remove_prefix():
    a = "abc/a.txt"
    assert remove_prefix(a, "abc/") == "a.txt"
    assert remove_prefix(a, "bcd/") == a


def test_oauth2password_bearer_cookie():
    app = FastAPI()
    oauth2_scheme = OAuth2PasswordBearerCookie(tokenUrl="token")
    oauth2_scheme_no_auto_error = OAuth2PasswordBearerCookie(
        tokenUrl="token", auto_error=False)

    @app.get("/protected")
    async def protected_route(token: str = Depends(oauth2_scheme)):
        return {"token": token}

    @app.get("/protected_no_auto_error")
    async def protected_route_no_auto_error(
            token: str = Depends(oauth2_scheme_no_auto_error)):
        return {"token": token}

    client = TestClient(app)

    resp = client.get("/protected")
    assert resp.status_code == 403

    response = client.get(
        "/protected", headers={"Authorization": "Bearer mytoken"})
    assert response.status_code == 200
    assert response.json() == {"token": "mytoken"}

    client.cookies.set("Authorization", "Bearer%20mytoken")
    response = client.get("/protected")
    assert response.status_code == 200
    assert response.json() == {"token": "mytoken"}

    client.cookies.set("Authorization", "")
    response = client.get(
        "/protected", headers={"Authorization": "Invalid mytoken"})
    assert response.status_code == 403

    client.cookies.set("Authorization", "Invalid%20mytoken")
    response = client.get("/protected")
    assert response.status_code == 403

    client.cookies.set("Authorization", "Bearer%20cookietoken")
    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer headertoken"},
    )
    assert response.status_code == 200
    assert response.json() == {"token": "headertoken"}

    client.cookies.set("Authorization", "")
    response = client.get("/protected_no_auto_error")
    assert response.status_code == 200
    assert response.json() == {"token": None}

    response = client.get(
        "/protected_no_auto_error",
        headers={"Authorization": "Bearer mytoken"})
    assert response.status_code == 200
    assert response.json() == {"token": "mytoken"}

    response = client.get(
        "/protected_no_auto_error",
        headers={"Authorization": "Invalid mytoken"})
    assert response.status_code == 200
    assert response.json() == {"token": None}
