from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

import models
from core.security import SECRET_KEY, ALGORITHM
from core.encryption import hmac_hash

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")   # phone_hash saqlanadi
        if sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # JWT sub — phone_hash (eski tokenlar uchun fallback: to'g'ridan-to'g'ri phone orqali)
    user = await models.User.find_one(models.User.phone_hash == sub)
    if user is None:
        # Eski token fallback: sub = plain phone edi
        user = await models.User.find_one(models.User.phone_hash == hmac_hash(sub))
    if user is None:
        raise credentials_exception
    return user
