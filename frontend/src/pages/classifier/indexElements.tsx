import styled from "styled-components";
import { colours } from "../../styles/colours";

export const RowContainer = styled.div`
  background: ${colours.CFIA_Background_White};
  color: ${colours.CFIA_Font_Black};
  display: flex;
  flex-direction: row;
  justify-content: center;
  align-items: center;
  min-width: 100%;
  max-width: 100%;
  height: fit-content;
  position: relative;
  z-index: 0;
  padding: 0px 0px 0px 0px;
`;

export const ColumnContainer = styled.div`
  background: ${colours.CFIA_Background_White};
  color: ${colours.CFIA_Font_Black};
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: 100%;
  max-width: 100%;
  height: fit-content;
`;

export const TopContent = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 0px 0px 0px 0px;
`;

export const LeftContent = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 60%;
  max-width: 60%;
  height: fit-content;
  z-index: 0;
  position: relative;
`;

export const InfoContent = styled.div`
  display: flex;
  flex-direction: column;
  align-items: start;
  justify-content: start;
  width: 19%;
  max-width: 19%;
  height: 100%;
  max-height: 100%;
  z-index: 0;
  position: relative;
`;

export const RightContent = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 40%;
  max-width: 40%;
  height: fit-content;
  padding: 0vw;
  z-index: 0;
  position: relative;
`;

export const WarningLabel = styled.div`
  background: #ffd700; // Corrected to camelCase
  width: 110%;
  height: 2.5vh;
  color: #ff4500;
  margin-bottom: 10px; // Corrected to camelCase
  margin-top: -6.4vh; // Corrected to camelCase
  text-align: center; // Corrected to camelCase
  font-size: 2vh; // Corrected to camelCase
  padding: 0 1.9vw;
`;
