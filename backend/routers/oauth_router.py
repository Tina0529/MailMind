"""
OAuth router - Zoho Mail OAuth 2.0 endpoints
"""
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional

from services.zoho_oauth_service import zoho_oauth_service
from config import settings


oauth_router = APIRouter()


class OAuthConfigRequest(BaseModel):
    """Request to set OAuth credentials"""
    client_id: str
    client_secret: str


class OAuthConfigResponse(BaseModel):
    """Response for OAuth configuration"""
    configured: bool
    auth_url: Optional[str] = None


class OAuthStatusResponse(BaseModel):
    """Response for OAuth status check"""
    connected: bool
    user_email: Optional[str] = None


@oauth_router.get("/auth-url", response_model=OAuthConfigResponse)
def get_auth_url():
    """Get the OAuth authorization URL"""
    # Ensure credentials are loaded from file
    zoho_oauth_service._load_credentials()

    # Check if we have client credentials (from settings or file)
    if not zoho_oauth_service.client_id or not zoho_oauth_service.client_secret:
        return OAuthConfigResponse(
            configured=False,
            auth_url=None
        )

    # Try to load existing tokens
    if zoho_oauth_service.load_tokens():
        # Test if tokens still work
        success, _ = zoho_oauth_service.test_connection()
        if success:
            return OAuthConfigResponse(
                configured=True,
                auth_url=None
            )

    # Generate new auth URL
    auth_url = zoho_oauth_service.get_auth_url()
    return OAuthConfigResponse(
        configured=False,
        auth_url=auth_url
    )


@oauth_router.post("/config", response_model=OAuthConfigResponse)
def configure_oauth(config: OAuthConfigRequest):
    """Configure OAuth credentials and return auth URL"""
    # Update service with new credentials
    zoho_oauth_service.client_id = config.client_id
    zoho_oauth_service.client_secret = config.client_secret

    # Save credentials to file
    zoho_oauth_service.save_credentials()

    # Generate auth URL
    auth_url = zoho_oauth_service.get_auth_url()

    return OAuthConfigResponse(
        configured=False,
        auth_url=auth_url
    )


@oauth_router.post("/callback")
def oauth_callback(code: str = Query(...), state: Optional[str] = Query(None)):
    """Handle OAuth callback and exchange code for tokens"""
    try:
        print(f"DEBUG: Received OAuth callback with code: {code[:20]}...")

        # Make sure we have the credentials loaded
        if not zoho_oauth_service.client_id or not zoho_oauth_service.client_secret:
            raise Exception("Client credentials not configured. Please configure OAuth first.")

        print(f"DEBUG: Client ID: {zoho_oauth_service.client_id[:20]}...")

        # Exchange code for tokens
        result = zoho_oauth_service.exchange_code_for_token(code)
        print(f"DEBUG: Token exchange successful")

        # Test connection to get user_email
        success, message = zoho_oauth_service.test_connection()
        print(f"DEBUG: Connection test - success: {success}, message: {message}")

        # Save tokens (after test_connection so user_email is included)
        zoho_oauth_service.save_tokens()

        if not success:
            raise Exception(message)

        return {
            "success": True,
            "message": message,
            "user_email": zoho_oauth_service.user_email
        }

    except Exception as e:
        print(f"ERROR: OAuth callback failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@oauth_router.get("/status", response_model=OAuthStatusResponse)
def get_oauth_status():
    """Get current OAuth connection status"""
    # Try to load tokens
    if not zoho_oauth_service.load_tokens():
        return OAuthStatusResponse(
            connected=False,
            user_email=None
        )

    # Test connection
    success, message = zoho_oauth_service.test_connection()

    return OAuthStatusResponse(
        connected=success,
        user_email=zoho_oauth_service.user_email if success else None
    )


@oauth_router.post("/disconnect")
def disconnect_oauth():
    """Disconnect and revoke OAuth tokens"""
    try:
        # Revoke tokens
        zoho_oauth_service.revoke_token()

        # Delete token file
        import os
        token_file = "data/zoho_tokens.json"
        if os.path.exists(token_file):
            os.remove(token_file)

        return {"success": True, "message": "Disconnected successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@oauth_router.post("/refresh")
def refresh_oauth_token():
    """Manually refresh the OAuth token"""
    try:
        result = zoho_oauth_service.refresh_access_token()
        zoho_oauth_service.save_tokens()

        return {
            "success": True,
            "message": "Token refreshed successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
