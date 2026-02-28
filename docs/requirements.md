# Requirements

## Functional Requirements

### FR-001: User Registration & Login
Users can register with email/password and log in to receive a JWT token.
**Acceptance criteria:**
- [x] POST /register creates user
- [x] POST /login returns JWT
- [x] GET /me returns current user from token
- [ ] Email verification flow (backend done, frontend missing)
- [ ] Password reset flow (backend done, frontend missing)

### FR-002: OAuth Authentication
Users can log in via Discord, Google, or Steam.
**Acceptance criteria:**
- [x] Discord OAuth flow working
- [ ] Google OAuth configured
- [ ] Steam OAuth configured
- [ ] Account linking (connect multiple providers to one account)

### FR-003: Game State Persistence
Users can save and load game state blobs.
**Acceptance criteria:**
- [x] CRUD operations for game state
- [x] User isolation (can only access own saves)

### FR-004: Multiplayer Matchmaking
Players can create/join rooms with WebSocket real-time sync.
**Acceptance criteria:**
- [x] Create room with code
- [x] Join room by code
- [x] Start game (host only)
- [x] WebSocket sync within room

### FR-005: Pinder Dating Game
Full dating game flow: profiles, swipes, matches, chat.
**Acceptance criteria:**
- [x] Profile CRUD
- [x] Swipe mechanics
- [x] Match detection
- [x] In-match chat

## Non-Functional Requirements

| Requirement | Target | Status |
|-------------|--------|--------|
| API latency (p99) | 200ms | Not measured |
| Test coverage | 80%+ | 26 tests passing |
| Rate limiting | Per-IP + per-user | Not implemented |
| HTTPS | Auto via Caddy | Working (prod) |
| DB migrations | Alembic | Not set up |
| Observability | Structured logs + health endpoint | /health exists |
