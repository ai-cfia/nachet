import styled from "styled-components";
import { colours } from "../../styles/colours";

export const BodyContainer = styled.div<{ width: number }>`
  background: ${colours.CFIA_Background_White};
  color: ${colours.CFIA_Font_Black};
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 0;
  max-width: 100%;
  padding: 0px 1.5vw;
  position: relative;
  margin-top: 6.5vh;
  margin-bottom: 10vh;
`;
