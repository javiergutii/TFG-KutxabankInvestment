import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { useEffect } from "react";
import LoginPage from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";

export default function App() {
  const isAuthenticated = useIsAuthenticated();
  const { instance } = useMsal();

  useEffect(() => {
    // Manejar el redirect de vuelta desde Microsoft
    instance.handleRedirectPromise().catch(console.error);
  }, [instance]);

  return isAuthenticated ? <Dashboard /> : <LoginPage />;
}