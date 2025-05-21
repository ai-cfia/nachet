// cookieDecoder.ts
import pako from "pako";
import { Base64 } from "js-base64";
import { jwtDecode } from "jwt-decode";

export function decodeAndDecompressCookie(encgzipss: string) {
  const urlSafeBase64DecodedString = Base64.toUint8Array(
    encgzipss.replace(/_/g, "/").replace(/-/g, "+"),
  );

  // Decompress gzip
  const gzipDecompressedArray = pako.inflate(urlSafeBase64DecodedString);
  const gzipDecompressedString = new TextDecoder("utf-8").decode(
    gzipDecompressedArray,
  );

  // Decode JWT
  const jwtDecodedObject = jwtDecode<{ CustomClaims: { email: string } }>(
    gzipDecompressedString,
  );
  //   console.log(JSON.stringify(jwtDecodedObject));

  return jwtDecodedObject;
}
