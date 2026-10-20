import os
from typing import Dict

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models import SubscriptionTier

security = HTTPBearer()


class CognitoAuth:
    def __init__(self):
        self.user_pool_id = os.getenv("COGNITO_USER_POOL_ID", "")
        self.client_id = os.getenv("COGNITO_CLIENT_ID", "")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.issuer = (
            f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
            if self.user_pool_id
            else ""
        )
        self.jwks_client = (
            jwt.PyJWKClient(f"{self.issuer}/.well-known/jwks.json", cache_keys=True)
            if self.issuer
            else None
        )

    def verify_token(self, token: str) -> Dict:
        """Verify a Cognito ID token and extract its tenant context."""
        if not self.jwks_client or not self.client_id:
            raise HTTPException(
                status_code=500,
                detail="Cognito authentication is not configured",
            )

        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256":
                raise jwt.InvalidAlgorithmError("Unexpected JWT signing algorithm")

            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={
                    "require": ["exp", "iat", "iss", "aud", "sub", "token_use"],
                },
            )

            if payload.get("token_use") != "id":
                raise jwt.InvalidTokenError("Expected a Cognito ID token")

            tenant_id = payload.get("custom:tenant_id")
            subscription_tier = payload.get("custom:subscription_tier", "basic")
            if not tenant_id:
                raise HTTPException(status_code=403, detail="No tenant ID found in token")

            try:
                tier = SubscriptionTier(subscription_tier)
            except ValueError as exc:
                raise HTTPException(
                    status_code=403,
                    detail="Invalid subscription tier in token",
                ) from exc

            user_groups = payload.get("cognito:groups", [])
            if not isinstance(user_groups, list) or not all(
                isinstance(group, str) for group in user_groups
            ):
                raise jwt.InvalidTokenError("Invalid Cognito groups claim")

            role = "admin" if any(
                group.endswith("-admins") for group in user_groups
            ) else "user"

            return {
                "user_id": payload["sub"],
                "tenant_id": tenant_id,
                "subscription_tier": tier,
                "email": payload.get("email"),
                "username": payload.get("cognito:username", payload.get("email")),
                "role": role,
                "cognito:groups": user_groups,
            }
        except HTTPException:
            raise
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(status_code=401, detail="Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail="Invalid authentication token") from exc
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Authentication failed") from exc


auth_service = CognitoAuth()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict:
    """Return the authenticated user and verified tenant context."""
    return auth_service.verify_token(credentials.credentials)
