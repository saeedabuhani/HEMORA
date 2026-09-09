import base64, hashlib, hmac, re, secrets
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
    if not re.fullmatch(r"[0-9]{1,9}",value) or int(value)==0: return False
    digits=re.sub(r"\D","",value).zfill(9)
    if len(digits)!=9: return False
    total=0
    for i,ch in enumerate(digits):
        n=int(ch)*(1 if i%2==0 else 2); total += n if n<10 else n-9
    return total%10==0
def national_id_hash(value:str)->str: return hmac.new(settings.national_id_hmac_key.encode(),re.sub(r"\D","",value).zfill(9).encode(),hashlib.sha256).hexdigest()
def _fernet():
    key=settings.national_id_encryption_key.encode() if settings.national_id_encryption_key else base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest())
    return Fernet(key)
def encrypt_national_id(value:str)->str: return _fernet().encrypt(re.sub(r"\D","",value).zfill(9).encode()).decode()
def decrypt_national_id(value:str)->str: return _fernet().decrypt(value.encode()).decode()
def mask_national_id(value:str)->str: return "*******"+re.sub(r"\D","",value).zfill(9)[-2:]
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"

def generate_temporary_password(length: int = 12) -> str:
    """A one-time password for a new patient account.

    Uses secrets, and omits characters that are easy to misread (0/O, 1/l/I)
    because a clinician usually reads this out or writes it down.
    """
    while True:
        candidate = "".join(secrets.choice(ALPHABET) for _ in range(length))
        if any(c.isupper() for c in candidate) and any(c.islower() for c in candidate) and any(c.isdigit() for c in candidate):
            return candidate + "!"

def create_token(user_id:int, role:str, kind:str="access"):
    ttl=timedelta(minutes=settings.access_token_minutes) if kind=="access" else timedelta(days=settings.refresh_token_days)
    now=datetime.now(timezone.utc); return jwt.encode({"sub":str(user_id),"role":role,"type":kind,"iat":now,"exp":now+ttl},settings.jwt_secret,algorithm="HS256")
def decode_token(token:str,kind:str="access"): 
    payload=jwt.decode(token,settings.jwt_secret,algorithms=["HS256"])
    if payload.get("type")!=kind: raise jwt.InvalidTokenError("wrong token type")
    return payload
