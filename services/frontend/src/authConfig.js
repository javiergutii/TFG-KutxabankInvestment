export const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || "TU_CLIENT_ID_AQUI",
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AZURE_TENANT_ID || "TU_TENANT_ID_AQUI"}`,
    redirectUri: import.meta.env.VITE_REDIRECT_URI || "http://localhost:3000",
  },
  cache: {
    cacheLocation: "sessionStorage",
    storeAuthStateInCookie: false,
  },
};

// Scopes para autenticarse con TU backend
export const loginRequest = {
  scopes: [
    `api://${import.meta.env.VITE_AZURE_CLIENT_ID || "TU_CLIENT_ID_AQUI"}/access_as_user`,
  ],
};

// Scopes para Graph API (SharePoint) — se piden por separado cuando se necesitan
export const graphRequest = {
  scopes: [
    "User.Read",
    "Files.ReadWrite",
    "Sites.ReadWrite.All",
  ],
};