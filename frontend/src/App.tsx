import { HashRouter as Router, Route, Routes } from "react-router-dom";
import { Fragment, useState, useEffect } from "react";
import Cookies from "js-cookie";
import { Navbar, Appbar } from "./components/header";
import Body from "./root/body";
import Footer from "./components/footer";
import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication } from "@azure/msal-browser";
import { NachetAuthProvider } from "./auth";

interface AppProps {
  basename: string;
  msalInstance: PublicClientApplication;
  apiScopeClaim: string;
}

function App({ basename, msalInstance, apiScopeClaim }: AppProps) {
  const [windowSize, setWindowSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });
  const [creativeCommonsPopupOpen, setCreativeCommonsPopupOpen] =
    useState<boolean>(() => {
      const existingAgreement = Cookies.get("creative-commons-agreement");
      return existingAgreement === undefined || existingAgreement === "false";
    });

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
      <MsalProvider instance={msalInstance}>
        <NachetAuthProvider apiScopeClaim={apiScopeClaim}>
          <Fragment>
            <Navbar />
            <Appbar windowSize={windowSize} />
            <Routes>
              <Route
                path="/"
                element={
                  <Body
                    windowSize={windowSize}
                    creativeCommonsPopupOpen={creativeCommonsPopupOpen}
                    setCreativeCommonsPopupOpen={setCreativeCommonsPopupOpen}
                    handleCreativeCommonsAgreement={
                      handleCreativeCommonsAgreement
                    }
                    apiScopeClaim={apiScopeClaim}
                  />
                }
              />
              {/* Catch-all route for OAuth callbacks and other paths */}
              <Route
                path="*"
                element={
                  <Body
                    windowSize={windowSize}
                    creativeCommonsPopupOpen={creativeCommonsPopupOpen}
                    setCreativeCommonsPopupOpen={setCreativeCommonsPopupOpen}
                    handleCreativeCommonsAgreement={
                      handleCreativeCommonsAgreement
                    }
                    apiScopeClaim={apiScopeClaim}
                  />
                }
              />
            </Routes>
            <Footer />
          </Fragment>
        </NachetAuthProvider>
      </MsalProvider>
    </Router>
  );
}

export default App;
