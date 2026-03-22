import pytest
from datetime import timedelta

def test_password_hash_and_verify():
    from app.core.auth import hash_password, verify_password
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)

def test_create_and_decode_token():
    from app.core.auth import create_access_token, decode_access_token
    token = create_access_token({"sub": "user-uuid-1", "role": "analyst"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user-uuid-1"
    assert payload["role"] == "analyst"

def test_expired_token_raises():
    from app.core.auth import create_access_token, decode_access_token
    token = create_access_token({"sub": "user-uuid-1"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(Exception):
        decode_access_token(token)

def test_invalid_token_raises():
    from app.core.auth import decode_access_token
    with pytest.raises(Exception):
        decode_access_token("not.a.valid.jwt")
