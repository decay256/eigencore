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

## Quick Start with Docker

```bash
# Clone the repo
git clone https://github.com/decay256/eigencore.git
cd eigencore

# Configure
cp .env.example .env
# Edit .env with your settings (OAuth keys, etc.)

# Start everything
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# Stop
docker compose down
```

**API is now running at:**
- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

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
├── Dockerfile                   # Container build instructions
├── docker-compose.yml           # Development stack
├── docker-compose.prod.yml      # Production stack with Caddy
├── Caddyfile                    # Reverse proxy config
└── .env.example                 # Configuration template
```

## API Endpoints

### Auth
- `POST /auth/register` — Create account with email/password
- `POST /auth/login` — Login, get JWT token
- `GET /auth/me` — Get current user info

### OAuth
- `GET /auth/discord` — Start Discord OAuth flow
- `GET /auth/google` — Start Google OAuth flow
- `GET /auth/steam` — Start Steam OAuth flow

### Game State
- `GET /games/{game_id}/state` — List all save slots
- `GET /games/{game_id}/state/{slot}` — Get a specific save
- `POST /games/{game_id}/state` — Create or update a save
- `DELETE /games/{game_id}/state/{slot}` — Delete a save

### Matchmaking
- `POST /rooms` — Create room, get join code
- `POST /rooms/join` — Join room by code
- `GET /rooms/{code}` — Get room info
- `POST /rooms/{code}/start` — Start game (host only)
- `WS /rooms/{code}/ws?token=...` — Real-time sync

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

# Edit Caddyfile - replace "api.yourdomain.com" with your domain
# Point your domain's DNS A record to the server IP

# Start production stack
docker compose -f docker-compose.prod.yml up -d
```

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
    private string apiUrl = "https://api.yourdomain.com";
    private string token;

    public async Task<bool> Login(string email, string password)
    {
        var loginData = new { email, password };
        var json = JsonUtility.ToJson(loginData);
        
        using (var request = UnityWebRequest.Post($"{apiUrl}/auth/login", json, "application/json"))
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
        
        using (var request = UnityWebRequest.Post($"{apiUrl}/games/{gameId}/state", json, "application/json"))
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
pytest
```

## License

MIT
