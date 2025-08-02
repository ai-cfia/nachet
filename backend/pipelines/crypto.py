import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv("./pipelines/.env.crypto.local")

KEY = os.getenv("DECRYPTION_KEY")
# VALUE = os.getenv("VALUE")
MODE = os.getenv("MODE")

COUNT = int(os.getenv("ITEMCOUNT", 0))
if COUNT < 1:
    raise ValueError("ITEMCOUNT must be at least 1")
items = [os.getenv(f"ITEM{i}") for i in range(1, COUNT + 1)]


def encrypt(value: str = "test"):
    print(Fernet(KEY).encrypt(value.encode()).decode())
    print()


def decrypt(value: str = "test"):
    print(Fernet(KEY).decrypt(value.encode()).decode())
    print()


def main():
    print("Starting the crypto pipeline")
    print(f"Mode: {MODE}")

    if MODE not in ["encrypt", "decrypt"]:
        raise ValueError("MODE must be either 'encrypt' or 'decrypt'")
    if not KEY:
        raise ValueError("DECRYPTION_KEY must be set in the environment variables")

    for item in items:
        if not item:
            raise ValueError(
                "All ITEM variables must be set in the environment variables"
            )
        print(f"Processing item: {item}")
        decrypt(item) if MODE == "decrypt" else encrypt(item)
    return 0


if __name__ == "__main__":
    main()
