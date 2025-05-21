import { HashRouter as Router, Route, Routes } from "react-router-dom";
import { useCallback, Fragment, useState, useEffect } from "react";
// import { v4 as uuidv4 } from "uuid";
import Cookies from "js-cookie";
import Navbar from "./components/header/navbar";
import Body from "./root/body";
import Footer from "./components/footer";
import Appbar from "./components/header/appbar";

interface AppProps {
  basename?: string;
}

function App({
  basename = process.env.REACT_APP_BASENAME ?? "/",
}: AppProps): JSX.Element {
  const [windowSize, setWindowSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });
  const [uuid, setUuid] = useState<string>("");
  // const [container_uuid, setContainerUuid] = useState<string>("");
  const [creativeCommonsPopupOpen, setCreativeCommonsPopupOpen] =
    useState<boolean>(false);
  const [switchLanguage, setSwitchLanguage] = useState<boolean>(false);
  const [signedIn, setSignedIn] = useState<boolean>(true);
  const [signUpOpen, setSignUpOpen] = useState<boolean>(false);

  const handleCreativeCommonsAgreement = (agree: boolean): void => {
    // set a cookie to remember the users choice for 10 years (user choice should be stored in authentication database in the future)
    if (agree) {
      Cookies.set("creative-commons-agreement", "true", { expires: 365 * 10 });
      console.log(
        "Creative Commons Agreement: ",
        Cookies.get("creative-commons-agreement"),
      );
    } else {
      Cookies.set("creative-commons-agreement", "false", { expires: 365 * 10 });
    }
    setCreativeCommonsPopupOpen(false);
  };

  const getCreativeCommonsAgreement = useCallback((): void => {
    // check if the user has already agreed to the creative commons agreement (cookie)
    const existingAgreement = Cookies.get("creative-commons-agreement");
    if (existingAgreement === undefined || existingAgreement === "false") {
      setCreativeCommonsPopupOpen(true);
    }
  }, []);

  useEffect(() => {
    getCreativeCommonsAgreement();
  }, [getCreativeCommonsAgreement]);

  useEffect(() => {
    // update window size on resize
    const handleResize = (): void => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };
    window.addEventListener("resize", handleResize);
    return (): void => {
      window.removeEventListener("resize", handleResize);
    };
  }, [windowSize]);

  return (
    <Router basename={basename}>
      <Fragment>
        <Navbar
          windowSize={windowSize}
          setSignedIn={setSignedIn}
          signedIn={signedIn}
          setSignUpOpen={setSignUpOpen}
          signUpOpen={signUpOpen}
        />
        <Appbar
          windowSize={windowSize}
          setSwitchLanguage={setSwitchLanguage}
          switchLanguage={switchLanguage}
        />
        <Routes>
          <Route
            path="/"
            element={
              <Body
                windowSize={windowSize}
                uuid={uuid}
                creativeCommonsPopupOpen={creativeCommonsPopupOpen}
                setCreativeCommonsPopupOpen={setCreativeCommonsPopupOpen}
                handleCreativeCommonsAgreement={handleCreativeCommonsAgreement}
                setSignUpOpen={setSignUpOpen}
                signUpOpen={signUpOpen}
                signedIn={signedIn}
                setSignedIn={setSignedIn}
                setUuid={setUuid}
              />
            }
          />
        </Routes>
        <Footer uuid={uuid} windowSize={windowSize} />
      </Fragment>
    </Router>
  );
}

export default App;
