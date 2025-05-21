import { useEffect, useState } from "react";
import { decodeTiff } from "../common";

export interface DecodedTiff {
  rgba: Uint8Array;
  width: number;
  height: number;
}

const useDecoderTiff = (imageSrc: string) => {
  const [decodedTiff, setDecodedTiff] = useState<DecodedTiff>({
    rgba: new Uint8Array(0),
    width: 0,
    height: 0,
  });
  useEffect(() => {
    void decodeTiff(imageSrc).then((dTiff: DecodedTiff) => {
      setDecodedTiff(dTiff);
    });
  }, [imageSrc]);

  return decodedTiff;
};

export default useDecoderTiff;
