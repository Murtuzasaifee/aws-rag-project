"""
Cognito authentication module for JWT validation.

Provides utilities for validating JWT tokens from AWS Cognito
and extracting user context for authorization.
"""

import json
import logging
import urllib.request
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode
from pydantic import BaseModel, Field

from ragapp.core.config import get_settings

logger = logging.getLogger(__name__)

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)


class UserContext(BaseModel):
    """Authenticated user context extracted from JWT claims."""

    user_id: str = Field(..., description="Unique user identifier (Cognito sub)")
    org_id: str = Field(..., description="Organization identifier")
    email: str = Field(..., description="User email address")
    groups: list[str] = Field(default=[], description="Cognito group memberships")
    token_use: str = Field(default="access", description="Token type (id or access)")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "org_id": "acme",
                "email": "user@example.com",
                "groups": ["admin", "users"],
                "token_use": "access",
            }
        }


class CognitoJWKSClient:
    """Client for fetching and caching Cognito JWKS."""

    _instance: Optional["CognitoJWKSClient"] = None
    _jwks_cache: Dict[str, Any] = {}
    _keys_cache: Dict[str, list] = {}

    def __new__(cls) -> "CognitoJWKSClient":
        """Singleton pattern for JWKS client."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_jwks(self, region: str, user_pool_id: str) -> Dict[str, Any]:
        """
        Fetch JWKS from Cognito or return cached version.

        Args:
            region: AWS region
            user_pool_id: Cognito User Pool ID

        Returns:
            JWKS dictionary with keys
        """
        cache_key = f"{region}/{user_pool_id}"

        if cache_key not in self._jwks_cache:
            jwks_url = (
                f"https://cognito-idp.{region}.amazonaws.com/"
                f"{user_pool_id}/.well-known/jwks.json"
            )

            try:
                with urllib.request.urlopen(
                    urllib.request.Request(
                        jwks_url,
                        headers={"Accept": "application/json"},
                    ),
                    timeout=10,
                ) as response:
                    self._jwks_cache[cache_key] = json.loads(response.read().decode())
            except Exception as e:
                logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication service unavailable",
                )

        return self._jwks_cache[cache_key]

    def get_signing_key(self, region: str, user_pool_id: str, kid: str) -> jwk.Key:
        """
        Get the signing key for a specific key ID.

        Args:
            region: AWS region
            user_pool_id: Cognito User Pool ID
            kid: Key ID from JWT header

        Returns:
            JWK key object
        """
        jwks = self.get_jwks(region, user_pool_id)

        for key_data in jwks.get("keys", []):
            if key_data.get("kid") == kid:
                return jwk.construct(key_data)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Global JWKS client instance
_jwks_client: Optional[CognitoJWKSClient] = None


def get_jwks_client() -> CognitoJWKSClient:
    """Get or create the JWKS client singleton."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = CognitoJWKSClient()
    return _jwks_client


async def validate_cognito_token(token: str) -> Dict[str, Any]:
    """
    Validate a JWT token from AWS Cognito.

    Args:
        token: The JWT access or ID token from Cognito

    Returns:
        Dictionary of decoded token claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings()

    # Check if Cognito is configured
    if not settings.cognito_user_pool_id:
        logger.warning("Cognito User Pool ID not configured, skipping token validation")
        # In development, return a mock user context
        if settings.environment == "development":
            return {
                "sub": "dev-user-123",
                "custom:org_id": "dev-org",
                "email": "dev@example.com",
                "cognito:groups": [],
                "token_use": "access",
            }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )

    # Decode header to get key ID
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token header",
            )
    except JWTError as e:
        logger.error(f"Failed to decode token header: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get signing key and verify token
    jwks_client = get_jwks_client()
    signing_key = jwks_client.get_signing_key(
        settings.cognito_region,
        settings.cognito_user_pool_id,
        kid,
    )

    try:
        # Decode and validate the token
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.cognito_app_client_id,
            issuer=f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/{settings.cognito_user_pool_id}",
            options={
                "verify_at_hash": False,  # ID token specific claim
                "require": ["sub", "token_use"],  # Required claims
            },
        )

        # Verify token_use is valid
        token_use = claims.get("token_use")
        if token_use not in ["id", "access"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token use",
            )

        # Log successful validation
        logger.debug(f"Token validated for user: {claims.get('sub')}")

        return claims

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"The access token expired\""},
        )
    except jwt.JWTClaimsError as e:
        logger.warning(f"Invalid claims: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token claims: {str(e)}",
        )
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def extract_org_id(claims: Dict[str, Any]) -> str:
    """
    Extract the organization ID from JWT claims.

    Args:
        claims: JWT claims dictionary

    Returns:
        Organization ID string

    Raises:
        HTTPException: If org_id is not found in claims
    """
    # Try custom claim first (Cognito custom attribute)
    org_id = claims.get("custom:org_id")

    if not org_id:
        # Fallback to development mode
        settings = get_settings()
        if settings.environment == "development":
            org_id = "dev-org"
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Organization ID not found in token",
            )

    return org_id


def extract_user_id(claims: Dict[str, Any]) -> str:
    """
    Extract the user ID from JWT claims.

    Args:
        claims: JWT claims dictionary

    Returns:
        User ID string (Cognito sub claim)
    """
    return claims.get("sub", "")


def extract_user_email(claims: Dict[str, Any]) -> str:
    """
    Extract the user email from JWT claims.

    Args:
        claims: JWT claims dictionary

    Returns:
        User email string
    """
    return claims.get("email", "")


def extract_user_groups(claims: Dict[str, Any]) -> list[str]:
    """
    Extract the user groups from JWT claims.

    Args:
        claims: JWT claims dictionary

    Returns:
        List of group names
    """
    groups = claims.get("cognito:groups", [])
    if isinstance(groups, str):
        return [groups]
    return groups or []


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> UserContext:
    """
    FastAPI dependency to get the current authenticated user.

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        UserContext with user information

    Raises:
        HTTPException: If authentication fails
    """
    # Check if credentials are provided
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Validate the token
    claims = await validate_cognito_token(token)

    # Extract user context from claims
    try:
        return UserContext(
            user_id=extract_user_id(claims),
            org_id=extract_org_id(claims),
            email=extract_user_email(claims),
            groups=extract_user_groups(claims),
            token_use=claims.get("token_use", "unknown"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract user context: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user context in token",
        )


async def get_current_active_user(
    current_user: UserContext = Depends(get_current_user),
) -> UserContext:
    """
    FastAPI dependency to get the current active user.
    Extends get_current_user with additional validation if needed.

    Args:
        current_user: User context from get_current_user

    Returns:
        UserContext with user information
    """
    # Additional checks can be added here (e.g., check if user is active in database)
    return current_user


# Optional: Role-based access control
class RoleChecker:
    """Dependency for checking if user has required roles."""

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: UserContext = Depends(get_current_user)) -> UserContext:
        """Check if user has any of the allowed roles."""
        if not any(role in user.groups for role in self.allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User must have one of the following roles: {', '.join(self.allowed_roles)}",
            )
        return user
