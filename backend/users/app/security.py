from pwdlib import PasswordHash

hashing_password = PasswordHash.recommended()
DUMMY_HASH = hashing_password.hash("dummypassword")

def get_password_hash(password):
    return hashing_password.hash(password)

def verify_password(plain_password, hashed_password):
    return hashing_password.verify(plain_password,hashed_password)
