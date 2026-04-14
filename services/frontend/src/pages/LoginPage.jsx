import { useMsal } from "@azure/msal-react";
import { loginRequest } from "../authConfig";

export default function LoginPage() {
  const { instance } = useMsal();

  const handleLogin = () => {
    instance.loginRedirect(loginRequest).catch(console.error);
  };

  return (
    <div className="login-root">
      <div className="login-bg">
        <div className="grid-lines" />
        <div className="glow" />
      </div>

      <div className="login-card">
        <div className="login-card-inner">
          <div className="logo-mark">
            <span className="logo-icon">▶</span>
          </div>

          <div className="login-header">
            <h1 className="login-title">
              Transcriptor<span className="accent">.</span>
            </h1>
            <p className="login-subtitle">
              Descarga · Transcribe · Archiva
            </p>
          </div>

          <div className="login-divider">
            <span>acceso corporativo</span>
          </div>

          <button className="ms-login-btn" onClick={handleLogin}>
            <svg className="ms-logo" viewBox="0 0 21 21" fill="none">
              <rect x="1" y="1" width="9" height="9" fill="#F25022" />
              <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
              <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
              <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
            </svg>
            Entrar con cuenta Microsoft
          </button>

          <p className="login-note">
            Solo cuentas de la organización autorizadas
          </p>
        </div>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        .login-root {
          font-family: 'Syne', sans-serif;
          min-height: 100vh;
          background: #080a0f;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          overflow: hidden;
        }

        .login-bg {
          position: absolute;
          inset: 0;
          pointer-events: none;
        }

        .grid-lines {
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
          background-size: 60px 60px;
        }

        .glow {
          position: absolute;
          top: -200px;
          left: 50%;
          transform: translateX(-50%);
          width: 700px;
          height: 500px;
          background: radial-gradient(ellipse, rgba(0, 200, 150, 0.08) 0%, transparent 70%);
        }

        .login-card {
          position: relative;
          z-index: 1;
          width: 100%;
          max-width: 420px;
          padding: 2px;
          background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.02));
          border-radius: 16px;
          animation: cardIn 0.6s cubic-bezier(0.16,1,0.3,1) both;
        }

        @keyframes cardIn {
          from { opacity: 0; transform: translateY(30px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }

        .login-card-inner {
          background: #0d1117;
          border-radius: 14px;
          padding: 3rem 2.5rem;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1.5rem;
        }

        .logo-mark {
          width: 56px;
          height: 56px;
          background: rgba(0, 200, 150, 0.1);
          border: 1px solid rgba(0, 200, 150, 0.25);
          border-radius: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .logo-icon {
          font-size: 1.4rem;
          color: #00c896;
        }

        .login-header {
          text-align: center;
        }

        .login-title {
          font-size: 2.2rem;
          font-weight: 800;
          color: #f0f4f8;
          letter-spacing: -0.03em;
          line-height: 1;
        }

        .accent {
          color: #00c896;
        }

        .login-subtitle {
          font-family: 'Space Mono', monospace;
          font-size: 0.7rem;
          color: #4a5568;
          letter-spacing: 0.15em;
          text-transform: uppercase;
          margin-top: 0.5rem;
        }

        .login-divider {
          width: 100%;
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .login-divider::before,
        .login-divider::after {
          content: '';
          flex: 1;
          height: 1px;
          background: rgba(255,255,255,0.06);
        }

        .login-divider span {
          font-family: 'Space Mono', monospace;
          font-size: 0.62rem;
          color: #2d3748;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          white-space: nowrap;
        }

        .ms-login-btn {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.85rem;
          padding: 0.9rem 1.5rem;
          background: #fff;
          color: #1a1a2e;
          font-family: 'Syne', sans-serif;
          font-size: 0.95rem;
          font-weight: 600;
          border: none;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.15s ease;
          letter-spacing: -0.01em;
        }

        .ms-login-btn:hover {
          background: #f0f4f8;
          transform: translateY(-1px);
          box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }

        .ms-login-btn:active {
          transform: translateY(0);
        }

        .ms-logo {
          width: 21px;
          height: 21px;
          flex-shrink: 0;
        }

        .login-note {
          font-family: 'Space Mono', monospace;
          font-size: 0.65rem;
          color: #2d3748;
          text-align: center;
          line-height: 1.6;
        }
      `}</style>
    </div>
  );
}