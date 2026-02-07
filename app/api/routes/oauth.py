from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from authlib.integrations.httpx_client import AsyncOAuth2Client
from datetime import datetime, UTC
import httpx

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserResponse
from app.core.security import create_access_token
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["oauth"])
settings = get_settings()


# Discord OAuth
@router.get("/discord")
async def discord_login():
    if not settings.discord_client_id:
        raise HTTPException(status_code=501, detail="Discord OAuth not configured")
    
    client = AsyncOAuth2Client(
        client_id=settings.discord_client_id,
        redirect_uri=settings.discord_redirect_uri,
    )
    uri, state = client.create_authorization_url(
        "https://discord.com/api/oauth2/authorize",
        scope="identify email",
    )
    return RedirectResponse(uri)


@router.get("/discord/callback")
async def discord_callback(code: str, db: AsyncSession = Depends(get_db)):
    if not settings.discord_client_id or not settings.discord_client_secret:
        raise HTTPException(status_code=501, detail="Discord OAuth not configured")
    
    async with httpx.AsyncClient() as client:
        # Exchange code for token
        token_response = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.discord_redirect_uri,
            },
        )
        token_data = token_response.json()
        
        if "access_token" not in token_data:
            raise HTTPException(status_code=400, detail="Failed to get Discord token")
        
        # Get user info
        user_response = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        discord_user = user_response.json()
    
    # Find or create user
    result = await db.execute(
        select(User).where(User.oauth_provider == "discord", User.oauth_id == discord_user["id"])
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            oauth_provider="discord",
            oauth_id=discord_user["id"],
            email=discord_user.get("email"),
            display_name=discord_user["username"],
            avatar_url=f"https://cdn.discordapp.com/avatars/{discord_user['id']}/{discord_user.get('avatar')}.png" if discord_user.get("avatar") else None,
            is_verified=discord_user.get("verified", False),
        )
        db.add(user)
    
    user.last_login = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)
    
    token = create_access_token({"sub": str(user.id)})
    
    # In production, redirect to your frontend with the token
    return {"access_token": token, "user": UserResponse.model_validate(user)}


# Google OAuth
@router.get("/google")
async def google_login():
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")
    
    client = AsyncOAuth2Client(
        client_id=settings.google_client_id,
        redirect_uri=settings.google_redirect_uri,
    )
    uri, state = client.create_authorization_url(
        "https://accounts.google.com/o/oauth2/v2/auth",
        scope="openid email profile",
    )
    return RedirectResponse(uri)


@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")
    
    async with httpx.AsyncClient() as client:
        # Exchange code for token
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.google_redirect_uri,
            },
        )
        token_data = token_response.json()
        
        if "access_token" not in token_data:
            raise HTTPException(status_code=400, detail="Failed to get Google token")
        
        # Get user info
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        google_user = user_response.json()
    
    # Find or create user
    result = await db.execute(
        select(User).where(User.oauth_provider == "google", User.oauth_id == google_user["id"])
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            oauth_provider="google",
            oauth_id=google_user["id"],
            email=google_user.get("email"),
            display_name=google_user.get("name", google_user.get("email", "User")),
            avatar_url=google_user.get("picture"),
            is_verified=google_user.get("verified_email", False),
        )
        db.add(user)
    
    user.last_login = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)
    
    token = create_access_token({"sub": str(user.id)})
    
    return {"access_token": token, "user": UserResponse.model_validate(user)}


# Steam OAuth (OpenID 2.0 - different flow)
@router.get("/steam")
async def steam_login(request: Request):
    if not settings.steam_api_key:
        raise HTTPException(status_code=501, detail="Steam OAuth not configured")
    
    # Steam uses OpenID 2.0
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": settings.steam_redirect_uri,
        "openid.realm": str(request.base_url),
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    url = "https://steamcommunity.com/openid/login?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/steam/callback")
async def steam_callback(request: Request, db: AsyncSession = Depends(get_db)):
    if not settings.steam_api_key:
        raise HTTPException(status_code=501, detail="Steam OAuth not configured")
    
    params = dict(request.query_params)
    
    # Verify with Steam
    params["openid.mode"] = "check_authentication"
    async with httpx.AsyncClient() as client:
        response = await client.post("https://steamcommunity.com/openid/login", data=params)
        if "is_valid:true" not in response.text:
            raise HTTPException(status_code=400, detail="Steam authentication failed")
    
    # Extract Steam ID
    claimed_id = params.get("openid.claimed_id", "")
    steam_id = claimed_id.split("/")[-1]
    
    # Get Steam user info
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={settings.steam_api_key}&steamids={steam_id}"
        )
        data = response.json()
        steam_user = data["response"]["players"][0] if data["response"]["players"] else None
    
    if not steam_user:
        raise HTTPException(status_code=400, detail="Failed to get Steam user info")
    
    # Find or create user
    result = await db.execute(
        select(User).where(User.oauth_provider == "steam", User.oauth_id == steam_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            oauth_provider="steam",
            oauth_id=steam_id,
            display_name=steam_user["personaname"],
            avatar_url=steam_user.get("avatarfull"),
        )
        db.add(user)
    
    user.last_login = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)
    
    token = create_access_token({"sub": str(user.id)})
    
    return {"access_token": token, "user": UserResponse.model_validate(user)}
