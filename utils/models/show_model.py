from pydantic import BaseModel, Field
from typing import List, Optional

class ShowQuality(BaseModel):
    """Schema for show episode quality information."""
    type: str = Field(..., description="Quality type (e.g., '1080p', '4K')")
    size: str = Field(..., description="File size in bytes")
    audio: str = Field(..., description="Audio language")
    video_codec: str = Field(..., description="Video codec used")
    file_type: str = Field(..., description="File type (e.g., 'mp4', 'mkv')")
    subtitle: str = Field(..., description="Subtitle language")
    runtime: int = Field(..., description="Movie runtime in minutes")
    file_hash: str = Field(None, description="File hash for verification")
    msg_id: int = Field(None, description="Message ID for the file")
    chat_id: int = Field(None, description="Chat ID for the file")


class Episode(BaseModel):
    """Schema for TV show episode."""
    episode_number: int = Field(..., description="Episode number")
    name: str = Field(..., description="Episode title")
    overview: Optional[str] = Field(None, description="Episode overview/summary")
    still_path: Optional[str] = Field(None, description="Path to episode still image")
    air_date: Optional[str] = Field(None, description="Episode air date")
    quality: List[ShowQuality] = Field(..., description="Available quality options")

class Season(BaseModel):
    """Schema for TV show season."""
    season_number: int = Field(..., description="Season number")
    episodes: List[Episode] = Field(..., description="List of episodes in the season")

class CastMember(BaseModel):
    """Schema for cast member information."""
    name: str = Field(..., description="Name of the cast member")
    character: str = Field(..., description="Character played by the cast member")
    imageUrl: Optional[str] = Field(None, description="Profile image path")

class ShowSchema(BaseModel):
    """Schema for TV show data validation."""
    sid: int = Field(..., description="Show ID from TMDB")
    title: str = Field(..., description="Show title")
    original_title: str = Field(..., description="Original show title")
    release_date: Optional[str] = Field(None, description="First air date")
    overview: Optional[str] = Field(None, description="Show overview/summary")
    poster_path: Optional[str] = Field(None, description="Poster image path")
    creators: List[str] = Field(None, description="List of creators")
    backdrop_path: Optional[str] = Field(None, description="Backdrop image path")
    popularity: Optional[float] = Field(None, description="Popularity score")
    vote_average: Optional[float] = Field(None, description="Average vote score")
    vote_count: Optional[int] = Field(None, description="Vote count")
    cast: List[CastMember] = Field(None, description="List of cast members")
    logo: str = Field(None, description="Logo image path")
    genres: Optional[List[str]] = Field(None, description="List of genre names")
    season: List[Season] = Field(..., description="List of seasons")
    links: Optional[List[str]] = Field(None, description="List of external links")
    studios: Optional[List[str]] = Field(None, description="List of production companies")
    total_episodes: Optional[int] = Field(None, description="Total number of episodes")
    total_seasons: Optional[int] = Field(None, description="Total number of seasons")
    status: Optional[str] = Field(None, description="Show status (e.g., 'Returning Series', 'Ended')")
    trailer: Optional[str] = Field(None, description="Trailer URL")
