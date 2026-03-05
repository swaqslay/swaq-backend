from passlib.context import CryptContext
import bcrypt

print(f"Bcrypt version: {getattr(bcrypt, '__version__', 'unknown')}")
try:
    print(f"Bcrypt __about__: {getattr(bcrypt, '__about__', 'missing')}")
except Exception as e:
    print(f"Error accessing bcrypt.__about__: {e}")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

try:
    hashed = pwd_context.hash("password")
    print(f"Hashed password: {hashed}")
except Exception as e:
    print(f"Error hashing password: {e}")
    import traceback
    traceback.print_exc()

long_password = "a" * 80
try:
    hashed = pwd_context.hash(long_password)
    print(f"Hashed long password: {hashed}")
except Exception as e:
    print(f"Error hashing long password: {e}")
