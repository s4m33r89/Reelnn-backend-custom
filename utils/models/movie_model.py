from pydantic import BaseModel, Field
from typing import List, Optional

class MovieQuality(BaseModel):
    """Schema for movie quality information."""
    type: str = Field(..., description="Quality type (e.g., '1080p', '4K')")
    size: str = Field(..., description="File size in a readable format")
    audio: str = Field(..., description="Audio language")
    video_codec: str = Field(..., description="Video codec used")
    file_type: str = Field(..., description="File type (e.g., 'mp4', 'mkv')")
    subtitle: str = Field(..., description="Subtitle language")
    file_hash: str = Field(None, description="File hash for verification")
    msg_id: int = Field(None, description="Message ID for the file")
    chat_id: int = Field(None, description="Chat ID for the file")

class CastMember(BaseModel):
    """Schema for cast member information."""
    name: str = Field(..., description="Name of the cast member")
    character: str = Field(..., description="Character played by the cast member")
    imageUrl: Optional[str] = Field(None, description="Profile image path")


class MovieSchema(BaseModel):
    """Schema for movie data validation."""
    mid: int = Field(..., description="Movie ID from TMDB")
    title: str = Field(..., description="Movie title")
    original_title: str = Field(..., description="Original movie title")
    release_date: Optional[str] = Field(None, description="Movie release date")
    overview: Optional[str] = Field(None, description="Movie overview")
    poster_path: Optional[str] = Field(None, description="Poster image path")
    runtime: int = Field(None, description="Movie runtime in minutes")
    backdrop_path: Optional[str] = Field(None, description="Backdrop image path")
    popularity: Optional[float] = Field(None, description="Popularity score")
    vote_average: Optional[float] = Field(None, description="Average vote score")
    directors: List[str] = Field(None, description="List of directors")
    vote_count: Optional[int] = Field(None, description="Vote count")
    cast: List[CastMember] = Field(None, description="List of cast members")
    logo: Optional[str] = Field(None, description="Logo image path")
    genres: Optional[List[str]] = Field(None, description="List of genre IDs")
    quality: List[MovieQuality] = Field(..., description="List of available qualities")
    links: Optional[List[str]] = Field(None, description="List of external links")
    studios: Optional[List[str]] = Field(None, description="List of production companies")
    trailer: Optional[str] = Field(None, description="Trailer URL")