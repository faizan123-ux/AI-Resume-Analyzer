import bcrypt
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "YOUR_SUPER_SECRET_KEY_CHANGE_THIS"
ALGORITHM = "HS256"

# പാസ്‌വേഡ് ഹാഷ് ചെയ്യാൻ (Direct bcrypt ഉപയോഗിച്ച്)
def hash_password(password: str) -> str:
    # പാസ്‌വേഡ് ടെക്സ്റ്റിനെ bytes ലേക്ക് മാറ്റി ഹാഷ് ചെയ്യുന്നു
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

# ലോഗിൻ ചെയ്യുമ്പോൾ പാസ്‌വേഡ് കറക്റ്റ് ആണോ എന്ന് നോക്കാൻ
def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)

# JWT ടോക്കൺ ഉണ്ടാക്കാൻ (പഴയത് പോലെ തന്നെ)
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# security.py ഫയലിന്റെ താഴെ ഇത് പേസ്റ്റ് ചെയ്യുക
# security.py-ൽ ഈ ഫങ്ക്ഷൻ മാത്രം മാറ്റി പേസ്റ്റ് ചെയ്യുക:
def verify_access_token(token: str):
    try:
        # ഇവിടെ കൃത്യമായി decode ചെയ്യുന്നു
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
        # ടോക്കൺ തെറ്റാണെങ്കിലോ എക്സ്പെയർ ആയാലോ None റിട്ടേൺ ചെയ്യും
        return None