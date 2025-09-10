import base64
import gzip
import jwt


def decode_vouch_cookie(encgzipss: str) -> str:
    url_safe_base64_decoded_string = base64.urlsafe_b64decode(encgzipss)
    gzip_decompressed_string = gzip.decompress(url_safe_base64_decoded_string).decode(
        "UTF-8"
    )
    jwt_decoded_object = jwt.decode(
        gzip_decompressed_string,
        algorithms=["HS256"],
        options={"verify_signature": False},
    )
    return jwt_decoded_object
