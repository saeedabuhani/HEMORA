import base64, hashlib, hmac, re
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from .config import settings

hasher=PasswordHasher()
def hash_password(value:str)->str: return hasher.hash(value)
def verify_password(value:str, encoded:str)->bool:
    try: return hasher.verify(encoded,value)
    except Exception: return False
def validate_israeli_id(value:str)->bool:
    """Format check only: exactly nine digits, the first of which is 1-9.

    The check-digit algorithm is deliberately not applied. This is a teaching
    demo, and requiring genuine check-digit-valid identifiers would force made
    up patients to carry numbers that look like real people's. The format rule
    still catches typos, wrong lengths and leading zeros.
    """
    return bool(re.fullmatch(r"[1-9][0-9]{8}", (value or "").strip()))
def national_id_hash(value:str)->str: return hmac.new(settings.national_id_hmac_key.encode(),_digits(value).encode(),hashlib.sha256).hexdigest()
def _digits(value:str)->str: return re.sub(r"\D","",value or "").zfill(9)
def _fernet():
    key=settings.national_id_encryption_key.encode() if settings.national_id_encryption_key else base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest())
    return Fernet(key)
def encrypt_national_id(value:str)->str: return _fernet().encrypt(_digits(value).encode()).decode()
def decrypt_national_id(value:str)->str: return _fernet().decrypt(value.encode()).decode()
def mask_national_id(value:str)->str: return "*******"+_digits(value)[-2:]
def create_token(user_id:int, role:str, kind:str="access"):
    ttl=timedelta(minutes=settings.access_token_minutes) if kind=="access" else timedelta(days=settings.refresh_token_days)
    now=datetime.now(timezone.utc); return jwt.encode({"sub":str(user_id),"role":role,"type":kind,"iat":now,"exp":now+ttl},settings.jwt_secret,algorithm="HS256")
def decode_token(token:str,kind:str="access"): 
    payload=jwt.decode(token,settings.jwt_secret,algorithms=["HS256"])
    if payload.get("type")!=kind: raise jwt.InvalidTokenError("wrong token type")
    return payload
