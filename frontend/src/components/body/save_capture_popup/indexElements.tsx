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
  justify-content: center;
  align-items: center;
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
