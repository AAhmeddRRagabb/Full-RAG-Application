

from pwdlib import PasswordHash
from pydantic import SecretStr
password_hasher = PasswordHash.recommended()


DUMMY_PASSWORD_HASH = password_hasher.hash(
    "dummy-password-used-for-timing-protection"
)

def hash_password(password: SecretStr) -> str:
    return password_hasher.hash(password = password.get_secret_value())

def verify_password(password: SecretStr, expected_password_hash: str) -> bool:
    return password_hasher.verify(
        password = password.get_secret_value(),
        hash = expected_password_hash
    )