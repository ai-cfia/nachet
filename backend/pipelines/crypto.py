import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv('./.env.crypto.local')

KEY = os.getenv("DECRYPTION_KEY")
VALUE = os.getenv("VALUE")
MODE = os.getenv("MODE")

def encrypt():
 print(Fernet(KEY).encrypt(VALUE.encode()).decode())

def decrypt():
 print(Fernet(KEY).decrypt(VALUE.encode()).decode())

def main():
    print("Starting the crypto pipeline")
    print(f"Mode: {MODE}")
    decrypt() if MODE == "decrypt" else encrypt()
    return 0

if __name__ == "__main__":
    main()
