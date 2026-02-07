# Eigencore

Game backend API for indie games — user accounts, game state persistence, and matchmaking.

## Features

- **User Authentication**
  - Email/password registration and login
  - OAuth: Discord, Google, Steam
  - JWT-based sessions

- **Game State Persistence**
  - Save/load game state per user
  - Multiple save slots per game
  - JSON-based flexible state storage

- **Matchmaking**
  - Room-code based matchmaking (Among Us style)
  - WebSocket support for real-time sync
  - Host controls for starting games

- **Web Frontend**
  - Dark, gaming-inspired login/register UI
  - OAuth button integration
  - Ready for white-labeling

## Quick Start with Docker

```bash
# Clone the repo
git clone https://github.com/decay256/eigencore.git
cd eigencore

# Configure
cp .env.example .env
# Edit .env with your settings (OAuth keys, etc.)

# Start API only (port 8000)
docker compose up -d

# Or start full stack with frontend (port 8080)
docker compose -f docker-compose.local.yml up -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# Stop
docker compose down
```

**Access:**
- Frontend: http://localhost:8080 (with docker-compose.local.yml)
- API: http://localhost:8000 (or :8080/api/v1/*)
- Swagger docs: http://localhost:8080/docs
- Health check: http://localhost:8080/health

## Project Structure

```
eigencore/
├── app/
│   ├── api/
│   │   ├── deps.py              # Auth dependencies
│   │   └── routes/
│   │       ├── auth.py          # Email/password auth
│   │       ├── oauth.py         # Discord/Google/Steam
│   │       ├── game_state.py    # Save/load game state
│   │       └── rooms.py         # Matchmaking + WebSocket
│   ├── core/
│   │   ├── config.py            # Settings from .env
│   │   └── security.py          # JWT + password hashing
│   ├── db/
│   │   └── database.py          # Async SQLAlchemy + PostgreSQL
│   ├── models/                  # Database models
│   └── schemas/                 # Pydantic schemas (API contracts)
├── frontend/                    # Static login/register UI
│   ├── index.html
│   └── static/
│       ├── styles.css
│       └── app.js
├── Dockerfile                   # Container build instructions
├── docker-compose.yml           # Development stack (API only)
├── docker-compose.local.yml     # Full stack with frontend (Caddy)
├── docker-compose.prod.yml      # Production stack
├── Caddyfile                    # Production reverse proxy
├── Caddyfile.local              # Local development (HTTP)
└── .env.example                 # Configuration template
```

## API Endpoints

All API routes are prefixed with `/api/v1`.

### Auth
- `POST /api/v1/auth/register` — Create account with email/password
- `POST /api/v1/auth/login` — Login (form data: username, password)
- `GET /api/v1/auth/me` — Get current user info

### OAuth
- `GET /api/v1/oauth/discord/authorize` — Start Discord OAuth flow
- `GET /api/v1/oauth/google/authorize` — Start Google OAuth flow
- `GET /api/v1/oauth/steam/authorize` — Start Steam OAuth flow

### Game State
- `GET /api/v1/games/{game_id}/state` — List all save slots
- `GET /api/v1/games/{game_id}/state/{slot}` — Get a specific save
- `POST /api/v1/games/{game_id}/state` — Create or update a save
- `DELETE /api/v1/games/{game_id}/state/{slot}` — Delete a save

### Matchmaking
- `POST /api/v1/rooms` — Create room, get join code
- `POST /api/v1/rooms/join` — Join room by code
- `GET /api/v1/rooms/{code}` — Get room info
- `POST /api/v1/rooms/{code}/start` — Start game (host only)
- `WS /ws/rooms/{code}?token=...` — Real-time sync

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required
SECRET_KEY=generate-a-strong-random-key

# Database (auto-configured in Docker)
DATABASE_URL=postgresql+asyncpg://eigencore:eigencore@postgres:5432/eigencore

# OAuth (optional, add as needed)
DISCORD_CLIENT_ID=...
DISCORD_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
STEAM_API_KEY=...
```

## Production Deployment

### Option 1: Single droplet with Docker Compose

```bash
# On your server
git clone https://github.com/decay256/eigencore.git
cd eigencore
cp .env.example .env
# Edit .env with production values

# Edit Caddyfile - replace "eigencore.yourdomain.com" with your domain
# Point your domain's DNS A record to the server IP

# Start production stack
docker compose -f docker-compose.prod.yml up -d
```

Caddy will automatically provision HTTPS certificates via Let's Encrypt.

### Option 2: Managed database + Docker

Use Neon, Supabase, or DigitalOcean Managed Postgres:
1. Create a managed Postgres instance
2. Set `DATABASE_URL` in `.env` to the connection string
3. Remove the `postgres` service from docker-compose
4. Deploy

### Scaling

```bash
# Scale to 3 API instances
docker compose -f docker-compose.prod.yml up -d --scale api=3

# For 10k concurrent users:
# - 4-6 API instances
# - Managed Postgres with connection pooling
# - Add Redis for WebSocket pub/sub
```

## Unity Integration

```csharp
// Example: Login and save game state
public class EigencoreClient : MonoBehaviour
{
    private string apiUrl = "https://eigencore.yourdomain.com";
    private string token;

    public async Task<bool> Login(string email, string password)
    {
        var form = new WWWForm();
        form.AddField("username", email);
        form.AddField("password", password);
        
        using (var request = UnityWebRequest.Post($"{apiUrl}/api/v1/auth/login", form))
        {
            await request.SendWebRequest();
            var response = JsonUtility.FromJson<TokenResponse>(request.downloadHandler.text);
            token = response.access_token;
            return true;
        }
    }

    public async Task SaveGame(string gameId, object state)
    {
        var saveData = new { game_id = gameId, state_data = state };
        var json = JsonUtility.ToJson(saveData);
        
        using (var request = UnityWebRequest.Post($"{apiUrl}/api/v1/games/{gameId}/state", json, "application/json"))
        {
            request.SetRequestHeader("Authorization", $"Bearer {token}");
            await request.SendWebRequest();
        }
    }
}
```

## Development

```bash
# Run without Docker (local development)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing

# Start Postgres (via Docker or local install)
docker run -d --name eigencore-db \
  -e POSTGRES_USER=eigencore \
  -e POSTGRES_PASSWORD=eigencore \
  -e POSTGRES_DB=eigencore \
  -p 5432:5432 \
  postgres:16-alpine

# Run with hot reload
uvicorn app.main:app --reload

# Run tests
pytest -v
```

## License

MIT
