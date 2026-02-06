from pydantic import BaseModel, Field
from typing import List, Optional, Any

class TrendingConfig(BaseModel):
    """Schema for trending configuration."""
    movie: List[int] = Field(default_factory=list, description="List of trending movie IDs")
    show: List[int] = Field(default_factory=list, description="List of trending show IDs")

class ConfigSchema(BaseModel):
    """Schema for configuration data."""
    key: str = Field(..., description="Unique identifier for the config")
    value: Any = Field(..., description="Configuration value")
    description: Optional[str] = Field(None, description="Description of the configuration")