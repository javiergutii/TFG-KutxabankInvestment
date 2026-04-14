// ============================================================
// authConfig.js — Configuración de Microsoft Authentication
// ============================================================
// Cuando el admin te dé las credenciales, rellena aquí:
//   - VITE_AZURE_CLIENT_ID  → Application (client) ID
//   - VITE_AZURE_TENANT_ID  → Directory (tenant) ID
//
// Puedes ponerlas en un archivo .env en la raíz del frontend:
//   VITE_AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
//   VITE_AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
// ============================================================

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

// Permisos que pedimos al usuario cuando hace login
export const loginRequest = {
  scopes: [
    "User.Read",
    "Files.ReadWrite",
    "Sites.ReadWrite.All",
  ],
};

// Permisos para llamar a Graph API (SharePoint)
export const graphConfig = {
  graphMeEndpoint: "https://graph.microsoft.com/v1.0/me",
};