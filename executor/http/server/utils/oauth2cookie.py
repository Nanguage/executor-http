"""
from:
    https://nilsdebruin.medium.com/fastapi-how-to-add-basic-and-cookie-authentication-a45c85ef47d3
"""
from typing import Optional

from fastapi.security import OAuth2
from fastapi import HTTPException
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel

from starlette.status import HTTP_403_FORBIDDEN
from starlette.requests import Request


class OAuth2PasswordBearerCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[dict] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(
            password={"tokenUrl": tokenUrl, "scopes": scopes})  # type: ignore
        super().__init__(
            flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        header_authorization = request.headers.get("Authorization")
        cookie_authorization = request.cookies.get("Authorization")

        header_scheme, header_param = get_authorization_scheme_param(
            header_authorization
        )

        if header_scheme.lower() == "bearer":
            authorization = True
            scheme = header_scheme
            param = header_param
        elif isinstance(cookie_authorization, str):
            cookie_scheme, cookie_param = get_authorization_scheme_param(
                cookie_authorization.replace("%20", " ", 1)
            )
            if cookie_scheme.lower() == "bearer":
                authorization = True
                scheme = cookie_scheme
                param = cookie_param
            else:
                authorization = False
        else:
            authorization = False

        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
                )
            else:
                return None
        return param
