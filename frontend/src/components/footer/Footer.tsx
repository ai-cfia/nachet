import { useEffect, useState } from "react";
import { useAccount } from "@azure/msal-react";
import { environment } from "../../environments/environment";
import {
  FooterContainer,
  FooterWrap,
  FooterLogo,
  FooterLink,
} from "./indexElements";
import CanadaLogo from "../../assets/Canada_logo.png";
import useBackendUrl from "@hooks/useBackendUrl";
import { pingBackend } from "@common/api";

interface params {
  windowSize: {
    width: number;
    height: number;
  };
}

const Footer: React.FC<params> = (props) => {
  const accountInfo = useAccount();
  const backendUrl = useBackendUrl();
  const [backendConnected, setBackendConnected] = useState<boolean | null>(
    null,
  );
  const [isGuest, setIsGuest] = useState<boolean>(true);

  // Check backend connectivity for guest users
  useEffect(() => {
    if (!isGuest || !backendUrl) {
      return;
    }

    const checkBackendConnectivity = async () => {
      try {
        const connected = await pingBackend({ backendUrl });
        setBackendConnected(connected);
      } catch (error) {
        console.error("Backend connectivity check failed:", error);
        setBackendConnected(false);
      }
    };

    // Initial check
    checkBackendConnectivity();

    // Periodic check every 30 seconds
    const interval = setInterval(checkBackendConnectivity, 30000);

    return () => clearInterval(interval);
  }, [isGuest, backendUrl]);

  useEffect(() => {
    const idTokenClaims = accountInfo?.idTokenClaims;
    const acctClaim = idTokenClaims?.acct as number | undefined;

    if (acctClaim === 0) {
      setIsGuest(false);
    } else {
      setIsGuest(true);
    }
  }, [accountInfo]);

  return (
    <FooterContainer height={props.windowSize.height}>
      <FooterWrap
        width={props.windowSize.width}
        height={props.windowSize.height}
      >
        <FooterLink href="https://github.com/ai-cfia">
          Developed by AI Lab
        </FooterLink>
        <FooterLink>
          {backendConnected ? "Connected ✓" : "Disconnected ✗"}
        </FooterLink>
        <FooterLink>
          {environment.version !== "" ? "Version: " + environment.version : ""}
        </FooterLink>
        <FooterLink> OID: {accountInfo?.idTokenClaims?.oid || ""} </FooterLink>
        <FooterLogo
          src={CanadaLogo}
          width={props.windowSize.width}
          height={props.windowSize.height}
        />
      </FooterWrap>
    </FooterContainer>
  );
};

export default Footer;
