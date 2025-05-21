import styled from "styled-components";
import { colours } from "../../styles/colours";

export const FooterContainer = styled.footer<{ height: number }>`
  background-color: ${colours.CFIA_Background_White};
  width: 100%;
  height: 5vh;
`;

export const FooterWrap = styled.div<{ width: number; height: number }>`
  padding: 0vh 0vh 0.8vh 0vh;
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: space-between;
  max-width: 100%;
  height: 5vh;
  margin: auto;
  position: relative;
  z-index: 0;
  padding-left: 1.5vw;
  padding-right: 1.5vw;
`;

export const InfoSection = styled.section`
  width: 100%;
  justfiy-content: space-between;
  z-index: 0;
`;

export const InfoWrap = styled.div`
  display: flex;
  flex-direction: row;
  justfiy-content: space-between;
  align-items: center;
  margin: auto;
  z-index: 0;

  @media screen and (max-width: 820px) {
    flex-direction: column;
  }
`;

export const FooterLogo = styled.img<{ width: number; height: number }>`
  width: 6vw;
  z-index: 0;
  align-self: center;
  height: fit-content;
`;

export const FooterLink = styled.a`
  color: ${colours.CFIA_Font_Black};
  font-size: 0.6vw;
  text-decoration: none;
  cursor: pointer;
  margin-bottom: auto;
  margin-top: auto;
  align-self: flex-start;
  z-index: 0;
`;
