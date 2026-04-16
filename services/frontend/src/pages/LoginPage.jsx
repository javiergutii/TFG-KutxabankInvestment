import { useMsal } from "@azure/msal-react";
import { loginRequest } from "../authConfig";

export default function LoginPage() {
  const { instance } = useMsal();
  const handleLogin = () => instance.loginRedirect(loginRequest).catch(console.error);

  return (
    <div className="login-root">
      <div className="login-left">
        <div className="left-content">
          <div className="brand-line" />
          <h1 className="brand-title">Kutxabank<br />Investment</h1>
          <p className="brand-tagline">Plataforma de Análisis<br />de Conferencias</p>
        </div>
        <div className="left-footer">© {new Date().getFullYear()} Kutxabank Investment. Uso interno.</div>
      </div>
      <div className="login-right">
        <div className="login-card">
          <div className="card-accent" />
          <h2 className="card-title">Acceso corporativo</h2>
          <p className="card-subtitle">Identifícate con tu cuenta de empresa para acceder a la plataforma.</p>
          <button className="ms-btn" onClick={handleLogin}>
            <svg width="20" height="20" viewBox="0 0 21 21" fill="none">
              <rect x="1" y="1" width="9" height="9" fill="#F25022"/>
              <rect x="11" y="1" width="9" height="9" fill="#7FBA00"/>
              <rect x="1" y="11" width="9" height="9" fill="#00A4EF"/>
              <rect x="11" y="11" width="9" height="9" fill="#FFB900"/>
            </svg>
            Iniciar sesión con Microsoft
          </button>
          <p className="card-note">Solo usuarios autorizados de Kutxabank Investment pueden acceder.</p>
        </div>
      </div>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=DM+Sans:wght@300;400;500&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        .login-root{font-family:'DM Sans',sans-serif;min-height:100vh;display:flex;background:#fff}
        .login-left{width:45%;background:#1A1A1A;display:flex;flex-direction:column;justify-content:space-between;padding:3.5rem;position:relative;overflow:hidden}
        .login-left::before{content:'';position:absolute;top:-100px;right:-100px;width:400px;height:400px;border-radius:50%;background:radial-gradient(circle,rgba(227,30,36,0.12) 0%,transparent 70%);pointer-events:none}
        .login-left::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;background:#E31E24}
        .left-content{margin-top:3rem}
        .brand-line{width:40px;height:3px;background:#E31E24;margin-bottom:2rem}
        .brand-title{font-family:'Playfair Display',serif;font-size:2.8rem;font-weight:600;color:#fff;line-height:1.15;margin-bottom:1.5rem}
        .brand-tagline{font-size:0.95rem;font-weight:300;color:#7A7A7A;line-height:1.7}
        .left-footer{font-size:0.72rem;color:#4a4a4a}
        .login-right{flex:1;display:flex;align-items:center;justify-content:center;padding:3rem;background:#f8f8f8}
        .login-card{width:100%;max-width:420px;background:#fff;border:1px solid #e8e8e8;border-top:3px solid #E31E24;border-radius:2px;padding:2.5rem;box-shadow:0 4px 32px rgba(0,0,0,0.06);animation:cardIn 0.5s ease both}
        @keyframes cardIn{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
        .card-accent{width:24px;height:2px;background:#E31E24;margin-bottom:1.25rem}
        .card-title{font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:600;color:#1A1A1A;margin-bottom:0.75rem}
        .card-subtitle{font-size:0.85rem;color:#7A7A7A;line-height:1.6;font-weight:300;margin-bottom:2rem}
        .ms-btn{width:100%;display:flex;align-items:center;justify-content:center;gap:0.75rem;padding:0.85rem 1.5rem;background:#1A1A1A;color:#fff;font-family:'DM Sans',sans-serif;font-size:0.9rem;font-weight:500;border:none;border-radius:2px;cursor:pointer;transition:all 0.2s ease;margin-bottom:1.5rem}
        .ms-btn:hover{background:#E31E24;transform:translateY(-1px);box-shadow:0 4px 16px rgba(227,30,36,0.25)}
        .card-note{font-size:0.72rem;color:#aaa;line-height:1.6;text-align:center}
        @media(max-width:768px){.login-left{display:none}.login-right{background:#fff}}
      `}</style>
    </div>
  );
}