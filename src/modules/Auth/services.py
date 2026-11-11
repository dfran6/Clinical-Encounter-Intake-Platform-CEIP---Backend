from datetime import timedelta
import time
import uuid

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from src.core.utils import create_access_token, decode_token, verify_password
from src.models.main_model import User
from src.modules.Auth.schemas import LoginModel
from src.core.redis import add_jti_to_blocklist, add_jtis_to_blocklist, token_in_blocklist

REFRESH_TOKEN_EXPIRY =2

class AuthService():

    async def logout(self, access_token_details: dict, refresh_token: str):
        refresh_details = decode_token(refresh_token)
        if not refresh_details or not refresh_details.get("refresh"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "A valid refresh token is required")

        access_user_id = access_token_details.get("user", {}).get("user_uid")
        refresh_user_id = refresh_details.get("user", {}).get("user_uid")
        access_session_id = access_token_details.get("user", {}).get("session_id")
        refresh_session_id = refresh_details.get("user", {}).get("session_id")
        access_jti = access_token_details.get("jti")
        refresh_jti = refresh_details.get("jti")
        if (
            not access_jti or not refresh_jti or not access_user_id
            or access_user_id != refresh_user_id
            or access_session_id != refresh_session_id
        ):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tokens do not belong to the same session")

        now = int(time.time())
        expiries = {
            access_jti: max(1, int(access_token_details.get("exp", now + 1)) - now),
            refresh_jti: max(1, int(refresh_details.get("exp", now + 1)) - now),
        }
        if access_session_id:
            expiries[f"session:{access_session_id}"] = expiries[refresh_jti]
        await add_jtis_to_blocklist(expiries)
        return {"message": "Logged out successfully"}

    async def login(self, form:LoginModel , session:AsyncSession):
        statement = select(User).where(User.email == form.email)
        result = await session.execute(statement)
        user = result.scalar_one_or_none()
        
        if user is not None:
            if not user.is_active:
                raise HTTPException(
                    status_code=403,
                    detail="Account is deactivated")
                
            password_valid = verify_password(form.password, user.password_hash)
        
            if password_valid:
                token_user_data = {
                    "email": user.email,
                    "user_uid": str(user.uid),
                    "role": user.role,
                    "is_active": user.is_active,
                    "session_id": str(uuid.uuid4()),
                }
                access_token = create_access_token(
                    user_data=token_user_data)
            
                refresh_token = create_access_token(
                    user_data=token_user_data,
                    refresh= True,
                    expiry= timedelta(days=REFRESH_TOKEN_EXPIRY)
                )
                
                return JSONResponse(
                    content={
                        "message": "Login succesful",
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "user":{
                            "email": user.email,
                            "uid": str(user.uid),
                            "role": user.role,
                            "is_active": user.is_active,
                        }
                    }
                )
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="invalid email or password")
   
   
    async def new_refresh_token(self, refresh_token: str, session: AsyncSession):
        token_details = decode_token(refresh_token)
        if not token_details or not token_details.get("refresh"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
        refresh_jti = token_details.get("jti")
        if not refresh_jti:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
        if await token_in_blocklist(refresh_jti):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token has been revoked")

        user_data = token_details.get("user", {})
        session_id = user_data.get("session_id")
        if session_id and await token_in_blocklist(f"session:{session_id}"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session has been logged out")
        try:
            user_id = uuid.UUID(str(user_data.get("user_uid")))
        except (TypeError, ValueError):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

        token_user_data = {
            "email": user.email,
            "user_uid": str(user.uid),
            "role": user.role,
            "is_active": user.is_active,
            "session_id": user_data.get("session_id"),
        }
        
        access_token = create_access_token(
            user_data=token_user_data)
    
        refresh_token = create_access_token(
            user_data=token_user_data,
            refresh= True,
            expiry= timedelta(days=REFRESH_TOKEN_EXPIRY)
        )

        await add_jti_to_blocklist(
            refresh_jti,
            max(1, int(token_details.get("exp", time.time() + 1)) - int(time.time())),
        )
        
        return JSONResponse(
            content={
                "message": "reset succesful",
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        )
        
   
