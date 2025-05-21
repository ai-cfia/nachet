import styled from "styled-components";

export const Overlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 20;
  display: flex;
  justify-content: center;
  align-items: center;
  transition:
    visibility 0.5s,
    opacity 0.5s;
`;

export const InfoContainer = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: start;
  align-items: start;
  padding-left: 1vw;
  padding-right: 1vw;
`;

export const ButtonWrap = styled.div`
    display flex;
    flex-direction: row;
    align-items: center;
    margin: auto;
    margin-top: 2vh;
    margin-bottom: 2vh;
`;

export const TextArea = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: center;
  margin: auto;
  overflow-y: auto;
  max-height: 25vw;
  padding-top: 10px;
  padding-bottom: 5px;
  word-wrap: break-word;
`;

export const Paragraph = styled.p`
  font-size: 1.1vh;
  font-weight: 500;
  color: black;
  text-align: left;
`;

export const Header = styled.h3`
  font-size: 1.3vh;
  font-weight: 600;
  color: black;
  text-align: left;
  margin-bottom: 0.5vh;
  margin-top: 0.5vh;
`;
