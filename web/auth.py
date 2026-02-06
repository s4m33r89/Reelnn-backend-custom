from fastapi import Depends, HTTPException, Query
from fastapi.security import APIKeyHeader
import jwt
from datetime import datetime, timedelta
from config import SITE_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD


token_header = APIKeyHeader(name="Authorization", auto_error=False)

async def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=1)):
    """Create a new JWT token."""
    to_encode = data.copy()
    expire = datetime.now() + expires_delta
    to_encode.update({"expiry": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, SITE_SECRET, algorithm="HS256")
    return encoded_jwt

async def verify_token(
    authorization: str = Depends(token_header),
    token: str = Query(None) 
):
    """Verify the JWT token from Authorization header or query param."""

    if not authorization and token:
        authorization = token
        
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
            
        decoded = jwt.decode(token, SITE_SECRET, algorithms=["HS256"])
        
        if "expiry" in decoded and decoded["expiry"] < datetime.now().timestamp():
            raise HTTPException(status_code=401, detail="Token has expired")
            
        return decoded
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=401, 
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def authenticate_user(username: str, password: str):
    """Authenticate a user and return token if valid."""

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return await create_access_token({"sub": username, "role": "admin"})
    return None