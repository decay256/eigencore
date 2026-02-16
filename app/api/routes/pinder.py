from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
from datetime import datetime

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from pydantic import BaseModel

router = APIRouter(prefix="/pinder", tags=["pinder"])

# Pydantic models for request/response
class PenisVisualData(BaseModel):
    skin_color: str
    size: float
    shape: str
    has_hat: bool = False
    has_glasses: bool = False
    has_accessories: bool = False
    hat_type: Optional[str] = None
    glasses_type: Optional[str] = None
    accessory_types: List[str] = []

class PersonalityTraits(BaseModel):
    confidence: float = 0.5
    creativity: float = 0.5
    intelligence: float = 0.5
    humor: float = 0.5
    romance: float = 0.5
    adventure: float = 0.5
    empathy: float = 0.5

class PenisProfileCreate(BaseModel):
    display_name: str
    age: int
    personality_prompt: str
    visual_data: PenisVisualData
    traits: PersonalityTraits
    interests: List[str] = []
    attractiveness_rating: int = 50

class PenisProfileResponse(BaseModel):
    profile_id: str
    display_name: str
    age: int
    personality_prompt: str
    visual_data: PenisVisualData
    traits: PersonalityTraits
    interests: List[str]
    attractiveness_rating: int
    compatibility: Optional[float] = None

class MatchRequest(BaseModel):
    count: int = 10
    player_profile: dict
    exclude_ids: List[str] = []

class SwipeRequest(BaseModel):
    target_profile_id: str
    direction: str  # "left" or "right"
    timestamp: str

class SwipeResponse(BaseModel):
    success: bool
    is_match: bool = False
    match_id: Optional[str] = None
    compatibility: Optional[float] = None
    message: str = ""

class ChatMessage(BaseModel):
    sender: str
    message: str
    timestamp: str
    is_from_player: bool

class ChatHistoryResponse(BaseModel):
    success: bool
    messages: List[dict] = []
    message: str = ""

class MessageSendRequest(BaseModel):
    match_id: str
    message: str
    timestamp: str

class MessageResponse(BaseModel):
    success: bool
    message: str = ""

# Simulated database - in production, these would be proper DB tables
profiles_db = {}
swipes_db = {}
matches_db = {}
chats_db = {}

@router.post("/profiles", response_model=dict)
async def upload_profile(
    profile_data: PenisProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload/update a penis profile for the current user
    """
    try:
        profile_id = str(uuid.uuid4())
        
        # Store profile data (in production, save to database)
        profiles_db[current_user.id] = {
            "profile_id": profile_id,
            "user_id": current_user.id,
            "display_name": profile_data.display_name,
            "age": profile_data.age,
            "personality_prompt": profile_data.personality_prompt,
            "visual_data": profile_data.visual_data.dict(),
            "traits": profile_data.traits.dict(),
            "interests": profile_data.interests,
            "attractiveness_rating": profile_data.attractiveness_rating,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "profile_id": profile_id,
            "message": "Profile uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile upload failed: {str(e)}"
        )

@router.post("/matches", response_model=dict)
async def fetch_matching_profiles(
    match_request: MatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch matching penis profiles based on compatibility
    """
    try:
        # Get user's excluded IDs (already swiped)
        user_swipes = swipes_db.get(current_user.id, {})
        already_swiped = set(user_swipes.keys())
        already_swiped.update(match_request.exclude_ids)
        
        # Generate mock matching profiles (in production, use ML algorithm)
        mock_profiles = []
        for i in range(min(match_request.count, 10)):
            profile_id = str(uuid.uuid4())
            
            # Skip if already swiped
            if profile_id in already_swiped:
                continue
                
            mock_profile = {
                "profile_id": profile_id,
                "display_name": f"TestPenis{i+1}",
                "age": 25 + (i * 3),
                "personality_prompt": f"A charming penis with personality type {i+1}",
                "visual_data": {
                    "skin_color": "#F4C2A1",
                    "size": 5.5 + (i * 0.3),
                    "shape": "standard",
                    "has_hat": i % 2 == 0,
                    "has_glasses": i % 3 == 0,
                    "has_accessories": i % 4 == 0
                },
                "traits": {
                    "confidence": 0.3 + (i * 0.1),
                    "creativity": 0.4 + (i * 0.1),
                    "intelligence": 0.5 + (i * 0.1),
                    "humor": 0.6 + (i * 0.1),
                    "romance": 0.4 + (i * 0.1),
                    "adventure": 0.3 + (i * 0.1),
                    "empathy": 0.5 + (i * 0.1)
                },
                "interests": ["gaming", "art", "music"],
                "attractiveness_rating": 60 + (i * 5),
                "compatibility": 0.6 + (i * 0.05)
            }
            mock_profiles.append(mock_profile)
            
        return {
            "success": True,
            "profiles": mock_profiles,
            "message": f"Found {len(mock_profiles)} matching profiles"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Match fetch failed: {str(e)}"
        )

@router.post("/swipes", response_model=SwipeResponse)
async def submit_swipe(
    swipe_request: SwipeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a swipe action and check for matches
    """
    try:
        user_id = current_user.id
        target_id = swipe_request.target_profile_id
        
        # Record the swipe
        if user_id not in swipes_db:
            swipes_db[user_id] = {}
        swipes_db[user_id][target_id] = {
            "direction": swipe_request.direction,
            "timestamp": swipe_request.timestamp
        }
        
        # Check for mutual match (simplified logic)
        is_match = False
        match_id = None
        compatibility = 0.0
        
        if swipe_request.direction == "right":
            # Simulate match probability based on compatibility
            compatibility = 0.6 + (hash(target_id) % 40) / 100  # Mock compatibility
            match_probability = compatibility * 0.8  # 80% of compatibility score
            
            # Simple match simulation
            import random
            if random.random() < match_probability:
                is_match = True
                match_id = str(uuid.uuid4())
                
                # Store the match
                matches_db[match_id] = {
                    "match_id": match_id,
                    "user1_id": user_id,
                    "user2_id": target_id,
                    "compatibility": compatibility,
                    "created_at": datetime.utcnow().isoformat()
                }
        
        return SwipeResponse(
            success=True,
            is_match=is_match,
            match_id=match_id,
            compatibility=compatibility,
            message="Swipe recorded successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Swipe submission failed: {str(e)}"
        )

@router.get("/chats/{match_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get chat history for a specific match
    """
    try:
        # Verify user has access to this match
        match = matches_db.get(match_id)
        if not match or current_user.id not in [match.get("user1_id"), match.get("user2_id")]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match not found or access denied"
            )
        
        # Get chat messages for this match
        chat_messages = chats_db.get(match_id, [])
        
        return ChatHistoryResponse(
            success=True,
            messages=chat_messages,
            message="Chat history retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat history fetch failed: {str(e)}"
        )

@router.post("/chats/send", response_model=MessageResponse)
async def send_chat_message(
    message_request: MessageSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a chat message to a match
    """
    try:
        match_id = message_request.match_id
        
        # Verify user has access to this match
        match = matches_db.get(match_id)
        if not match or current_user.id not in [match.get("user1_id"), match.get("user2_id")]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match not found or access denied"
            )
        
        # Add message to chat history
        if match_id not in chats_db:
            chats_db[match_id] = []
            
        chat_message = {
            "sender": current_user.email,  # Or username if available
            "message": message_request.message,
            "timestamp": message_request.timestamp,
            "is_from_player": True
        }
        
        chats_db[match_id].append(chat_message)
        
        return MessageResponse(
            success=True,
            message="Message sent successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Message send failed: {str(e)}"
        )

@router.get("/stats", response_model=dict)
async def get_pinder_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get Pinder game statistics for the current user
    """
    try:
        user_id = current_user.id
        user_swipes = swipes_db.get(user_id, {})
        user_matches = [m for m in matches_db.values() if m.get("user1_id") == user_id or m.get("user2_id") == user_id]
        
        stats = {
            "total_swipes": len(user_swipes),
            "total_matches": len(user_matches),
            "swipe_right_count": sum(1 for s in user_swipes.values() if s["direction"] == "right"),
            "swipe_left_count": sum(1 for s in user_swipes.values() if s["direction"] == "left"),
            "match_rate": len(user_matches) / max(len(user_swipes), 1) * 100,
            "average_compatibility": sum(m.get("compatibility", 0) for m in user_matches) / max(len(user_matches), 1)
        }
        
        return {
            "success": True,
            "stats": stats,
            "message": "Stats retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stats fetch failed: {str(e)}"
        )