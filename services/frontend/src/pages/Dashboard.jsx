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
    try { setLoading(true); const data = await getJobs(instance, accounts); setJobs(data); }
    catch (e) { console.error(e); } finally { setLoading(false); }
  }, [instance, accounts]);

  useEffect(() => { fetchJobs(); const i = setInterval(fetchJobs, 15000); return () => clearInterval(i); }, [fetchJobs]);

  const handleLogout = () => instance.logoutRedirect({ postLogoutRedirectUri: "/" });
  const handleJobLaunched = (j) => { setJobs((p) => [j, ...p]); setActiveTab("history"); };
  const initials = account?.name?.split(" ").map((n) => n[0]).slice(0, 2).join("") || "U";

  return (
    <div className="dr">
      <header className="tb">
        <div className="tb-brand">
          <div className="tb-dot" />
          <span className="tb-name">Kutxabank Investment</span>
          <span className="tb-sep" />
          <span className="tb-prod">Transcriptor</span>
        </div>
        <div className="tb-user">
          <div className="u-av">{initials}</div>
          <div className="u-info">
            <span className="u-name">{account?.name}</span>
            <span className="u-email">{account?.username}</span>
          </div>
          <button className="logout" onClick={handleLogout} title="Cerrar sesión">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        </div>
      </header>
      <div className="db">
        <aside className="sb">
          <nav className="sb-nav">
            <button className={`ni ${activeTab==="new"?"active":""}`} onClick={() => setActiveTab("new")}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
              Nueva transcripción
            </button>
            <button className={`ni ${activeTab==="history"?"active":""}`} onClick={() => setActiveTab("history")}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              Historial
              {jobs.length > 0 && <span className="nb">{jobs.length}</span>}
            </button>
          </nav>
        </aside>
        <main className="dm">
          <div className="dh">
            <div><div className="ha"/><h1 className="dt">{activeTab==="new"?"Nueva transcripción":"Historial de trabajos"}</h1>
            <p className="ds">{activeTab==="new"?"Introduce la URL del webcast y obtén los datos de acceso":`${jobs.length} trabajo${jobs.length!==1?"s":""} registrado${jobs.length!==1?"s":""}`}</p></div>
            {activeTab==="history" && <button className="rb" onClick={fetchJobs} disabled={loading}>Actualizar</button>}
          </div>
          <div className="dc">
            {activeTab==="new"
              ? <JobForm msalInstance={instance} accounts={accounts} onJobLaunched={handleJobLaunched}/>
              : <JobHistory jobs={jobs} loading={loading} msalInstance={instance} accounts={accounts} onRefresh={fetchJobs}/>}
          </div>
        </main>
      </div>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=DM+Sans:wght@300;400;500&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        .dr{font-family:'DM Sans',sans-serif;min-height:100vh;background:#f4f4f4;color:#1A1A1A;display:flex;flex-direction:column}
        .tb{height:56px;background:#1A1A1A;border-bottom:3px solid #E31E24;display:flex;align-items:center;justify-content:space-between;padding:0 2rem;position:sticky;top:0;z-index:100}
        .tb-brand{display:flex;align-items:center;gap:.75rem}
        .tb-dot{width:8px;height:8px;background:#E31E24;border-radius:50%}
        .tb-name{font-family:'Playfair Display',serif;font-size:.95rem;font-weight:600;color:#fff}
        .tb-sep{width:1px;height:16px;background:#3a3a3a}
        .tb-prod{font-size:.75rem;color:#7A7A7A;font-weight:300;letter-spacing:.08em;text-transform:uppercase}
        .tb-user{display:flex;align-items:center;gap:.75rem}
        .u-av{width:30px;height:30px;border-radius:50%;background:#E31E24;display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:500;color:#fff;flex-shrink:0}
        .u-info{display:flex;flex-direction:column}
        .u-name{font-size:.78rem;font-weight:500;color:#fff;line-height:1.2}
        .u-email{font-size:.65rem;color:#7A7A7A;line-height:1.2}
        .logout{background:transparent;border:1px solid #3a3a3a;color:#7A7A7A;width:30px;height:30px;border-radius:2px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .15s}
        .logout:hover{border-color:#E31E24;color:#E31E24}
        .db{flex:1;display:flex}
        .sb{width:220px;background:#fff;border-right:1px solid #e8e8e8;padding:1.5rem 0;flex-shrink:0}
        .sb-nav{display:flex;flex-direction:column;gap:2px;padding:0 .75rem}
        .ni{display:flex;align-items:center;gap:.6rem;padding:.65rem .85rem;border-radius:2px;border:none;background:transparent;color:#7A7A7A;font-family:'DM Sans',sans-serif;font-size:.83rem;font-weight:400;cursor:pointer;transition:all .15s;text-align:left;width:100%}
        .ni:hover{background:#f4f4f4;color:#1A1A1A}
        .ni.active{background:#fff5f5;color:#E31E24;font-weight:500;border-left:2px solid #E31E24;padding-left:calc(.85rem - 2px)}
        .nb{margin-left:auto;background:#E31E24;color:#fff;font-size:.62rem;padding:.1rem .45rem;border-radius:10px;min-width:18px;text-align:center}
        .dm{flex:1;display:flex;flex-direction:column;overflow-y:auto}
        .dh{padding:2rem 2.5rem 1.5rem;background:#fff;border-bottom:1px solid #e8e8e8;display:flex;align-items:flex-end;justify-content:space-between}
        .ha{width:24px;height:2px;background:#E31E24;margin-bottom:.85rem}
        .dt{font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:600;color:#1A1A1A;margin-bottom:.25rem}
        .ds{font-size:.78rem;color:#7A7A7A;font-weight:300}
        .rb{font-family:'DM Sans',sans-serif;font-size:.75rem;color:#7A7A7A;background:transparent;border:1px solid #e8e8e8;padding:.4rem .85rem;border-radius:2px;cursor:pointer;transition:all .15s}
        .rb:hover:not(:disabled){color:#1A1A1A;border-color:#1A1A1A}
        .dc{flex:1;padding:2rem 2.5rem}
      `}</style>
    </div>
  );
}