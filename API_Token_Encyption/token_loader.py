import base64
import hashlib
import getpass
from cryptography.fernet import Fernet

def generate_key(password: str) -> bytes:
    """
    Derives a 32-byte key from the provided password using SHA256.
    """
    return base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())

def load_token(enc_file_path: str) -> str:
    """
    Prompts for a password and decrypts the token from the specified encrypted file.

    Parameters:
        enc_file_path (str): Path to the .enc file containing the encrypted token.

    Returns:
        str: The decrypted token.
    """
    password = getpass.getpass("🔐 Enter token decryption password: ")
    
     # 🔍 Paste this line right here
    #print(f"[DEBUG] Decrypting with: {password}")
    
    key = generate_key(password)
    f = Fernet(key)

    try:
        with open(enc_file_path, "rb") as file:
            encrypted_data = file.read()
        decrypted_token = f.decrypt(encrypted_data).decode()
        return decrypted_token
    except Exception as e:
        raise RuntimeError(f"Failed to load or decrypt token: {e}")

# Example usage in another script:
# from token_loader import load_token
# TOKEN = load_token("path/to/token.enc")
