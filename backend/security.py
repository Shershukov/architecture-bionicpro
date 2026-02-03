import requests
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional

KEYCLOAK_URL = "http://keycloak:8080"
REALM = "reports-realm"
CLIENT_ID = "reports-backend"
ALGORITHMS = ["RS256"]

class KeycloakJWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> dict:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=401, detail="Invalid authentication scheme")
            return self.verify_jwt(credentials.credentials)
        else:
            raise HTTPException(status_code=401, detail="Invalid authorization code")

    def verify_jwt(self, token: str) -> dict:
        try:
            jwks_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs"
            jwks = requests.get(jwks_url).json()
            unverified_header = jwt.get_unverified_header(token)
            rsa_key = {}

            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"]
                    }

            if rsa_key:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=ALGORITHMS,
                    audience=CLIENT_ID
                )
                return payload
            else:
                raise HTTPException(status_code=401, detail="Unable to find appropriate key")

        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

def require_prothetic_role(token_payload: dict = Depends(KeycloakJWTBearer())):
    roles = []
    if "realm_access" in token_payload and "roles" in token_payload["realm_access"]:
        roles.extend(token_payload["realm_access"]["roles"])
    if "resource_access" in token_payload and CLIENT_ID in token_payload["resource_access"]:
        if "roles" in token_payload["resource_access"][CLIENT_ID]:
            roles.extend(token_payload["resource_access"][CLIENT_ID]["roles"])

    if "prothetic_user" not in roles:
        raise HTTPException(
            status_code=403,
            detail="Доступ запрещен"
        )

    return token_payload

auth_dependency = Depends(require_prothetic_role)