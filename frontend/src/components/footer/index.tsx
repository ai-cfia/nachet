import { environment } from "../../environments/environment";
import {
  FooterContainer,
  FooterWrap,
  FooterLogo,
  FooterLink,
} from "./indexElements";
import CanadaLogo from "../../assets/Canada_logo.png";

interface params {
  windowSize: {
    width: number;
    height: number;
  };
  uuid: string;
}

const Footer: React.FC<params> = (props) => {
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
          {environment.version !== "" ? "Version: " + environment.version : ""}{" "}
          | UUID: {props.uuid}
        </FooterLink>
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
