import styled from "styled-components";
import { colours } from "../../../styles/colours";

export const AppbarWrap = styled.div<{ width: number; height: number }>`
  background-color: ${colours.CFIA_Background_Blue};
  color: ${colours.CFIA_Font_White};
  height: 3.5vh;
  display: flex;
  justify-content: center;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 3;
  box-shadow: 0 0 5px 0 rgba(0, 0, 0, 0.5);
`;

export const AppbarContainer = styled.div<{ width: number; height: number }>`
  display: flex;
  justify-content: space-between;
  z-index: 3;
  width: 100%;
  padding: 0 1.5vw;
  height: 2.8vh;
`;

export const AppbarHeader = styled.h2`
  color: ${colours.CFIA_Font_White};
  font-size: 1.4vh;
  font-weight: bold;
  text-decoration: none;
  display: flex;
  align-items: center;
  justify-self: flex-start;
  z-index: 3;
`;
