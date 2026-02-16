# Pinder Dating Game API

Complete REST API for the Pinder penis dating/flirting game. All endpoints require authentication except where noted.

## Base URL
- Production: `https://core.dk-eigenvektor.de/api/v1/pinder`
- Development: `http://localhost:8000/api/v1/pinder`

## Authentication
All endpoints require a valid JWT token in the `Authorization` header:
```http
Authorization: Bearer <your_jwt_token>
```

## Endpoints

### Profile Management

#### Upload Profile
Upload or update a penis profile for the current user.

**POST** `/profiles`

**Request Body:**
```json
{
  "display_name": "SexyPenis69",
  "age": 25,
  "personality_prompt": "A confident, humorous penis with a love for adventure and deep conversations",
  "visual_data": {
    "skin_color": "#F4C2A1",
    "size": 6.2,
    "shape": "standard",
    "has_hat": true,
    "has_glasses": false,
    "has_accessories": true,
    "hat_type": "fedora",
    "glasses_type": null,
    "accessory_types": ["bow_tie", "chain"]
  },
  "traits": {
    "confidence": 0.8,
    "creativity": 0.7,
    "intelligence": 0.6,
    "humor": 0.9,
    "romance": 0.7,
    "adventure": 0.8,
    "empathy": 0.6
  },
  "interests": ["gaming", "music", "travel", "art"],
  "attractiveness_rating": 85
}
```

**Response:**
```json
{
  "success": true,
  "profile_id": "uuid-here",
  "message": "Profile uploaded successfully"
}
```

### Matchmaking

#### Fetch Matching Profiles
Get a list of compatible penis profiles for swiping.

**POST** `/matches`

**Request Body:**
```json
{
  "count": 10,
  "player_profile": {},
  "exclude_ids": ["already-swiped-id-1", "already-swiped-id-2"]
}
```

**Response:**
```json
{
  "success": true,
  "profiles": [
    {
      "profile_id": "match-id-123",
      "display_name": "CutePenis42",
      "age": 28,
      "personality_prompt": "A creative, empathetic penis who loves art",
      "visual_data": {
        "skin_color": "#F4C2A1",
        "size": 5.5,
        "shape": "standard",
        "has_hat": false,
        "has_glasses": true,
        "has_accessories": false,
        "glasses_type": "round"
      },
      "traits": {
        "confidence": 0.6,
        "creativity": 0.9,
        "intelligence": 0.8,
        "humor": 0.7,
        "romance": 0.8,
        "adventure": 0.5,
        "empathy": 0.9
      },
      "interests": ["art", "philosophy", "cooking"],
      "attractiveness_rating": 78,
      "compatibility": 0.82
    }
  ],
  "message": "Found 1 matching profiles"
}
```

### Swiping System

#### Submit Swipe
Record a swipe action and check for mutual matches.

**POST** `/swipes`

**Request Body:**
```json
{
  "target_profile_id": "profile-to-swipe-on",
  "direction": "right",
  "timestamp": "2026-02-16T09:00:00.000Z"
}
```

**Response (No Match):**
```json
{
  "success": true,
  "is_match": false,
  "match_id": null,
  "compatibility": 0.0,
  "message": "Swipe recorded successfully"
}
```

**Response (Match!):**
```json
{
  "success": true,
  "is_match": true,
  "match_id": "match-uuid-here",
  "compatibility": 0.73,
  "message": "Swipe recorded successfully"
}
```

### Chat System

#### Get Chat History
Retrieve chat messages for a specific match.

**GET** `/chats/{match_id}`

**Response:**
```json
{
  "success": true,
  "messages": [
    {
      "sender": "user@example.com",
      "message": "Hey there! You seem interesting 😊",
      "timestamp": "2026-02-16T09:01:00.000Z",
      "is_from_player": true
    },
    {
      "sender": "match@example.com",
      "message": "Thanks! I love your adventurous spirit!",
      "timestamp": "2026-02-16T09:02:00.000Z",
      "is_from_player": false
    }
  ],
  "message": "Chat history retrieved successfully"
}
```

#### Send Chat Message
Send a message to a match.

**POST** `/chats/send`

**Request Body:**
```json
{
  "match_id": "match-uuid-here",
  "message": "Want to go on a digital adventure together?",
  "timestamp": "2026-02-16T09:03:00.000Z"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Message sent successfully"
}
```

### Statistics

#### Get User Stats
Retrieve game statistics for the current user.

**GET** `/stats`

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_swipes": 42,
    "total_matches": 7,
    "swipe_right_count": 28,
    "swipe_left_count": 14,
    "match_rate": 16.67,
    "average_compatibility": 0.68
  },
  "message": "Stats retrieved successfully"
}
```

## Data Models

### PenisVisualData
Visual customization data for penis appearance.

```typescript
interface PenisVisualData {
  skin_color: string;        // Hex color code
  size: number;              // 1.0 - 10.0 scale
  shape: string;             // "standard", "curved", "thick", etc.
  has_hat: boolean;
  has_glasses: boolean;
  has_accessories: boolean;
  hat_type?: string;         // "fedora", "beanie", "cap", etc.
  glasses_type?: string;     // "round", "square", "aviator", etc.
  accessory_types: string[]; // ["bow_tie", "chain", "piercing", etc.]
}
```

### PersonalityTraits
Personality scores (0.0 - 1.0) used for compatibility matching.

```typescript
interface PersonalityTraits {
  confidence: number;   // How bold and self-assured
  creativity: number;   // Artistic and innovative thinking
  intelligence: number; // Intellectual curiosity and wit
  humor: number;        // Sense of humor and playfulness
  romance: number;      // Romantic and emotional connection
  adventure: number;    // Love for new experiences
  empathy: number;      // Understanding and caring for others
}
```

### Compatibility Algorithm
Matches are scored based on personality trait compatibility:

1. **Trait Differences**: Smaller differences = higher compatibility
2. **Complementary Traits**: Some opposites attract (confidence + empathy)
3. **Shared Interests**: Common interests boost compatibility
4. **Visual Preferences**: Basic visual appeal factors
5. **Random Factor**: 10-20% randomness for serendipity

**Formula**: `compatibility = (trait_match * 0.4) + (interest_match * 0.3) + (visual_appeal * 0.2) + (random_factor * 0.1)`

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common error codes:
- `401 Unauthorized`: Missing or invalid authentication token
- `404 Not Found`: Match not found or access denied
- `422 Unprocessable Entity`: Invalid request data
- `500 Internal Server Error`: Server-side error

## Rate Limiting

No rate limiting currently implemented, but recommended limits:
- Profile uploads: 1 per minute
- Match requests: 10 per minute  
- Swipes: 100 per hour
- Messages: 20 per minute

## Testing

Comprehensive test suite covers:
- Authentication requirements
- Data validation
- Success/error scenarios
- Integration workflows
- Performance testing

Run tests: `pytest tests/test_pinder.py -v`

## Unity Integration

Complete Unity client provided in `EigenCoreIntegration.cs`:
- Async HTTP requests
- Token-based authentication
- Event-driven architecture
- Error handling and retry logic
- Local data caching

See `/Assets/Scripts/Core/EigenCoreIntegration.cs` in the Unity project.