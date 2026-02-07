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

## Quick Start

```bash
# Clone and setup
cd eigencore
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Setup PostgreSQL
createdb eigencore

# Run
uvicorn app.main:app --reload
```

## API Endpoints

### Auth
- `POST /auth/register` — Create account
- `POST /auth/login` — Login
- `GET /auth/me` — Get current user

### OAuth
- `GET /auth/discord` — Discord login
- `GET /auth/google` — Google login
- `GET /auth/steam` — Steam login

### Game State
- `GET /games/{game_id}/state` — List save slots
- `GET /games/{game_id}/state/{slot}` — Get save
- `POST /games/{game_id}/state` — Create/update save
- `DELETE /games/{game_id}/state/{slot}` — Delete save

### Rooms
- `POST /rooms` — Create room (returns code)
- `POST /rooms/join` — Join by code
- `GET /rooms/{code}` — Get room info
- `POST /rooms/{code}/start` — Start game
- `WS /rooms/{code}/ws` — Real-time sync

## Unity Integration

```csharp
// Example: Save game state
var state = new { plants = myPlants, sun = sunPosition };
var json = JsonUtility.ToJson(state);

using (var client = new HttpClient())
{
    client.DefaultRequestHeaders.Authorization = 
        new AuthenticationHeaderValue("Bearer", token);
    
    var content = new StringContent(json, Encoding.UTF8, "application/json");
    await client.PostAsync($"{API_URL}/games/plant-sim/state", content);
}
```

## License

MIT
