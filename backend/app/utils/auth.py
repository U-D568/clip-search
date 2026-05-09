import bcrypt


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_passwd(plain, hashed) -> bool:
    b_plain = plain.encode("utf-8")
    b_hashed = hashed.encode("utf-8")
    return bcrypt.checkpw(b_plain, b_hashed)
