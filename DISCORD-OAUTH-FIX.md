# Discord OAuth Fix - COMPLETED ✅

## Problem
- Discord redirect URI was pointing to `http://104.248.27.154:8080/api/v1/auth/discord/callback` (raw IP)
- Should use HTTPS domain: `https://core.dk-eigenvektor.de/api/v1/auth/discord/callback`

## Solution Applied
✅ **Updated .env file** with correct HTTPS URLs:
```bash
DISCORD_REDIRECT_URI=https://core.dk-eigenvektor.de/api/v1/auth/discord/callback
GOOGLE_REDIRECT_URI=https://core.dk-eigenvektor.de/api/v1/auth/google/callback  
STEAM_REDIRECT_URI=https://core.dk-eigenvektor.de/api/v1/auth/steam/callback
```

✅ **Containers restarted** - new environment variables loaded
✅ **OAuth endpoint tested** - redirects to Discord authorization page correctly
✅ **Environment verified** - correct redirect URI loaded in container

## Discord Application Configuration
**Application ID:** 1470049713616064585
**Current Redirect URI:** `https://core.dk-eigenvektor.de/api/v1/auth/discord/callback`

### ⚠️ Required Manual Step
The Discord application on Discord Developer Portal needs to be updated with the new redirect URI:

1. Go to https://discord.com/developers/applications/1470049713616064585
2. Navigate to OAuth2 → General 
3. Add redirect URI: `https://core.dk-eigenvektor.de/api/v1/auth/discord/callback`
4. Save changes

## Testing Status
✅ **OAuth URL Generation** - Works, redirects to Discord  
⚠️ **Full OAuth Flow** - Needs Discord app redirect URI update  
✅ **Google/Steam URLs** - Fixed for future use

## Next Steps
1. Update Discord application redirect URI (manual step)
2. Test complete OAuth flow end-to-end
3. Test Google/Steam OAuth when needed

---
*Fixed: 2026-02-15 by Eigen*