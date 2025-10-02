import { HashRouter as Router, Route, Routes } from "react-router-dom";
import { useCallback, Fragment, useState, useEffect } from "react";
import Cookies from "js-cookie";
import { Navbar } from "./components/header";
import Body from "./root/body";
import Footer from "./components/footer";
import Appbar from "./components/header/appbar";
import LoadingIndicator from "./components/body/loading_indicator";
import {
  MsalProvider,
  // useMsal,
  // useAccount,
  MsalAuthenticationTemplate,
  MsalAuthenticationResult,
} from "@azure/msal-react";
import {
  InteractionType,
  AccountInfo,
  PublicClientApplication,
} from "@azure/msal-browser";

interface AppProps {
  basename: string;
  msalInstance: PublicClientApplication;
  apiScopeClaim: string;
}

// Add scopes here for ID token to be used at UserInfo endpoint
// const loginRequest: PopupRequest = {
//   // scopes: ["openid", "profile", "email"],
//   scopes: ["scopes.nachet.user"],
// };

function ErrorComponent({ error }: MsalAuthenticationResult) {
  return <p>An Error Occurred: {error?.errorMessage}</p>;
}

function App({ basename, msalInstance, apiScopeClaim }: AppProps) {
  const [windowSize, setWindowSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });
  const [uuid, setUuid] = useState<string>("");
  const [creativeCommonsPopupOpen, setCreativeCommonsPopupOpen] =
    useState<boolean>(false);
  const [switchLanguage, setSwitchLanguage] = useState<boolean>(false);
  const [userAccount, setUserAccount] = useState<AccountInfo | null>(null);

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
      <MsalProvider instance={msalInstance}>
        <Fragment>
          <Navbar
            windowSize={windowSize}
            setUuid={setUuid}
            setUserAccount={setUserAccount}
            apiScopeClaim={apiScopeClaim}
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
                <MsalAuthenticationTemplate
                  interactionType={InteractionType.Redirect}
                  authenticationRequest={{
                    scopes: [apiScopeClaim ?? ""],
                    // scopes: [
                    //   "User.Read",
                    //   "openid",
                    //   "profile",
                    //   "offline_access",
                    // ],
                  }}
                  errorComponent={ErrorComponent}
                  loadingComponent={LoadingIndicator}
                >
                  <Body
                    windowSize={windowSize}
                    uuid={uuid}
                    creativeCommonsPopupOpen={creativeCommonsPopupOpen}
                    setCreativeCommonsPopupOpen={setCreativeCommonsPopupOpen}
                    handleCreativeCommonsAgreement={
                      handleCreativeCommonsAgreement
                    }
                    user={userAccount}
                    apiScopeClaim={apiScopeClaim}
                  />
                </MsalAuthenticationTemplate>
              }
            />
          </Routes>
          <Footer uuid={uuid} windowSize={windowSize} />
        </Fragment>
      </MsalProvider>
    </Router>
  );
}

export default App;
