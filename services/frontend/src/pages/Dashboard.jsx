import { useMsal, useAccount } from "@azure/msal-react";
import { useState, useEffect, useCallback } from "react";
import JobForm from "../components/JobForm";
import JobHistory from "../components/JobHistory";
import { getJobs } from "../lib/api";

export default function Dashboard() {
  const { instance, accounts } = useMsal();
  const account = useAccount(accounts[0] || {});
  const [jobs, setJobs] = useState([]);
  const [activeTab, setActiveTab] = useState("new");
  const [loading, setLoading] = useState(false);

  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getJobs(instance, accounts);
      setJobs(data);
    } catch (e) {
      console.error("Error cargando trabajos:", e);
    } finally {
      setLoading(false);
    }
  }, [instance, accounts]);

  useEffect(() => {
    fetchJobs();
    // Polling cada 15s para actualizar estados
    const interval = setInterval(fetchJobs, 15000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const handleLogout = () => {
    instance.logoutRedirect({ postLogoutRedirectUri: "/" });
  };

  const handleJobLaunched = (newJob) => {
    setJobs((prev) => [newJob, ...prev]);
    setActiveTab("history");
  };

  const firstName = account?.name?.split(" ")[0] || "Usuario";
  const initials = account?.name
    ?.split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("") || "U";

  return (
    <div className="dash-root">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span className="sidebar-logo-icon">▶</span>
          <span className="sidebar-logo-text">Transcriptor</span>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activeTab === "new" ? "active" : ""}`}
            onClick={() => setActiveTab("new")}
          >
            <span className="nav-icon">＋</span>
            Nueva transcripción
          </button>
          <button
            className={`nav-item ${activeTab === "history" ? "active" : ""}`}
            onClick={() => setActiveTab("history")}
          >
            <span className="nav-icon">◎</span>
            Historial
            {jobs.length > 0 && (
              <span className="nav-badge">{jobs.length}</span>
            )}
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="user-avatar">{initials}</div>
            <div className="user-info">
              <span className="user-name">{firstName}</span>
              <span className="user-email">{account?.username}</span>
            </div>
          </div>
          <button className="logout-btn" onClick={handleLogout} title="Cerrar sesión">
            ⎋
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="dash-main">
        <div className="dash-header">
          <div>
            <h2 className="dash-title">
              {activeTab === "new" ? "Nueva transcripción" : "Historial de trabajos"}
            </h2>
            <p className="dash-subtitle">
              {activeTab === "new"
                ? "Introduce la URL del webcast y los datos de acceso"
                : `${jobs.length} trabajo${jobs.length !== 1 ? "s" : ""} registrado${jobs.length !== 1 ? "s" : ""}`}
            </p>
          </div>
          {activeTab === "history" && (
            <button className="refresh-btn" onClick={fetchJobs} disabled={loading}>
              {loading ? "↻" : "↺"} Actualizar
            </button>
          )}
        </div>

        <div className="dash-content">
          {activeTab === "new" ? (
            <JobForm
              msalInstance={instance}
              accounts={accounts}
              onJobLaunched={handleJobLaunched}
            />
          ) : (
            <JobHistory
              jobs={jobs}
              loading={loading}
              msalInstance={instance}
              accounts={accounts}
              onRefresh={fetchJobs}
            />
          )}
        </div>
      </main>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        .dash-root {
          font-family: 'Syne', sans-serif;
          min-height: 100vh;
          background: #080a0f;
          color: #e2e8f0;
          display: flex;
        }

        /* ── Sidebar ── */
        .sidebar {
          width: 240px;
          min-height: 100vh;
          background: #0d1117;
          border-right: 1px solid rgba(255,255,255,0.05);
          display: flex;
          flex-direction: column;
          padding: 1.5rem 1rem;
          position: sticky;
          top: 0;
          height: 100vh;
        }

        .sidebar-logo {
          display: flex;
          align-items: center;
          gap: 0.6rem;
          padding: 0.5rem 0.75rem;
          margin-bottom: 2rem;
        }

        .sidebar-logo-icon {
          font-size: 1rem;
          color: #00c896;
        }

        .sidebar-logo-text {
          font-size: 1.1rem;
          font-weight: 800;
          color: #f0f4f8;
          letter-spacing: -0.02em;
        }

        .sidebar-nav {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .nav-item {
          display: flex;
          align-items: center;
          gap: 0.6rem;
          padding: 0.65rem 0.75rem;
          border-radius: 8px;
          border: none;
          background: transparent;
          color: #4a5568;
          font-family: 'Syne', sans-serif;
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.15s;
          text-align: left;
          width: 100%;
        }

        .nav-item:hover {
          background: rgba(255,255,255,0.04);
          color: #e2e8f0;
        }

        .nav-item.active {
          background: rgba(0,200,150,0.1);
          color: #00c896;
        }

        .nav-icon {
          font-size: 0.9rem;
          width: 18px;
          text-align: center;
        }

        .nav-badge {
          margin-left: auto;
          background: rgba(0,200,150,0.15);
          color: #00c896;
          font-family: 'Space Mono', monospace;
          font-size: 0.65rem;
          padding: 0.1rem 0.4rem;
          border-radius: 4px;
        }

        .sidebar-footer {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding-top: 1rem;
          border-top: 1px solid rgba(255,255,255,0.05);
        }

        .user-chip {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 0.6rem;
          min-width: 0;
        }

        .user-avatar {
          width: 32px;
          height: 32px;
          border-radius: 8px;
          background: linear-gradient(135deg, #00c896, #0066cc);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.7rem;
          font-weight: 700;
          color: #fff;
          flex-shrink: 0;
        }

        .user-info {
          display: flex;
          flex-direction: column;
          min-width: 0;
        }

        .user-name {
          font-size: 0.8rem;
          font-weight: 600;
          color: #e2e8f0;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .user-email {
          font-family: 'Space Mono', monospace;
          font-size: 0.58rem;
          color: #4a5568;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .logout-btn {
          background: transparent;
          border: none;
          color: #4a5568;
          font-size: 1rem;
          cursor: pointer;
          padding: 0.25rem;
          border-radius: 4px;
          transition: color 0.15s;
          flex-shrink: 0;
        }

        .logout-btn:hover { color: #e2e8f0; }

        /* ── Main ── */
        .dash-main {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-height: 100vh;
          overflow-y: auto;
        }

        .dash-header {
          padding: 2rem 2.5rem 1.5rem;
          border-bottom: 1px solid rgba(255,255,255,0.05);
          display: flex;
          align-items: flex-end;
          justify-content: space-between;
        }

        .dash-title {
          font-size: 1.5rem;
          font-weight: 800;
          color: #f0f4f8;
          letter-spacing: -0.02em;
        }

        .dash-subtitle {
          font-family: 'Space Mono', monospace;
          font-size: 0.68rem;
          color: #4a5568;
          margin-top: 0.3rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        .refresh-btn {
          font-family: 'Space Mono', monospace;
          font-size: 0.72rem;
          color: #4a5568;
          background: transparent;
          border: 1px solid rgba(255,255,255,0.07);
          padding: 0.4rem 0.85rem;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.15s;
        }

        .refresh-btn:hover:not(:disabled) {
          color: #e2e8f0;
          border-color: rgba(255,255,255,0.15);
        }

        .dash-content {
          flex: 1;
          padding: 2rem 2.5rem;
        }
      `}</style>
    </div>
  );
}