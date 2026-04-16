import { useState } from "react";
import { getJobStatus } from "../lib/api";

const STATUS_CONFIG = {
  pending: { label: "En cola",    color: "#7A7A7A", bg: "#f4f4f4" },
  running: { label: "Procesando", color: "#b07800", bg: "#fffbf0" },
  done:    { label: "Completado", color: "#1a7a3a", bg: "#f0faf4" },
  error:   { label: "Error",      color: "#E31E24", bg: "#fff5f5" },
};

function formatDate(d) {
  if (!d) return "—";
  return new Date(d).toLocaleString("es-ES", { day:"2-digit", month:"2-digit", year:"numeric", hour:"2-digit", minute:"2-digit" });
}

function JobRow({ job, msalInstance, accounts }) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;

  const handleExpand = async () => {
    if (!expanded && !detail) {
      setLoadingDetail(true);
      try { const d = await getJobStatus(msalInstance, accounts, job.id); setDetail(d); }
      catch (e) { console.error(e); } finally { setLoadingDetail(false); }
    }
    setExpanded(v => !v);
  };

  return (
    <div className={`row ${expanded?"expanded":""}`}>
      <div className="row-header" onClick={handleExpand}>
        <div className="status-pill" style={{ background: cfg.bg, color: cfg.color }}>{cfg.label}</div>
        <div className="row-info">
          <span className="row-empresa">{job.empresa || "Sin nombre"}</span>
          <span className="row-url">{job.url?.slice(0, 70)}…</span>
        </div>
        <div className="row-meta">
          <span className="row-date">{formatDate(job.created_at)}</span>
          <span className="row-user">{job.user_name}</span>
        </div>
        <span className="chevron">{expanded ? "▲" : "▼"}</span>
      </div>

      {expanded && (
        <div className="row-detail">
          {loadingDetail ? <p className="dl-loading">Cargando detalles…</p> : detail ? (
            <>
              <div className="dl-grid">
                <div className="dl-item"><span className="dl-label">Estado</span><span className="dl-val" style={{color:cfg.color}}>{cfg.label}</span></div>
                <div className="dl-item"><span className="dl-label">Empresa</span><span className="dl-val">{detail.empresa}</span></div>
                <div className="dl-item"><span className="dl-label">Iniciado por</span><span className="dl-val">{detail.user_name||"—"}</span></div>
                <div className="dl-item"><span className="dl-label">SharePoint</span><span className="dl-val">
                  {detail.sharepoint_url ? <a href={detail.sharepoint_url} target="_blank" rel="noreferrer" className="sp-link">Ver archivo ↗</a> : "Pendiente"}
                </span></div>
              </div>
              {detail.url && <div className="dl-item"><span className="dl-label">URL del webcast</span><span className="dl-val mono">{detail.url}</span></div>}
              {detail.resumen && <div className="dl-summary"><span className="dl-label">Resumen</span><p className="summary-text">{detail.resumen}</p></div>}
              {detail.error_msg && <div className="dl-error"><span className="dl-label">Error</span><p className="error-text">{detail.error_msg}</p></div>}
            </>
          ) : <p className="dl-loading">No se pudieron cargar los detalles.</p>}
        </div>
      )}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=DM+Sans:wght@300;400;500&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        .row{background:#fff;border:1px solid #e8e8e8;border-radius:2px;overflow:hidden;transition:border-color .15s;font-family:'DM Sans',sans-serif}
        .row:hover,.row.expanded{border-color:#1A1A1A}
        .row-header{display:flex;align-items:center;gap:1rem;padding:1rem 1.25rem;cursor:pointer;user-select:none}
        .status-pill{font-size:.68rem;font-weight:500;padding:.25rem .65rem;border-radius:2px;white-space:nowrap;flex-shrink:0}
        .row-info{flex:1;display:flex;flex-direction:column;gap:.2rem;min-width:0}
        .row-empresa{font-size:.88rem;font-weight:500;color:#1A1A1A}
        .row-url{font-family:'Courier New',monospace;font-size:.65rem;color:#7A7A7A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .row-meta{display:flex;flex-direction:column;align-items:flex-end;gap:.2rem;flex-shrink:0}
        .row-date{font-size:.72rem;color:#7A7A7A}
        .row-user{font-size:.68rem;color:#aaa}
        .chevron{color:#aaa;font-size:.6rem;flex-shrink:0}
        .row-detail{padding:1.25rem;border-top:1px solid #f0f0f0;display:flex;flex-direction:column;gap:1rem}
        .dl-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem}
        .dl-item{display:flex;flex-direction:column;gap:.3rem}
        .dl-label{font-size:.65rem;color:#7A7A7A;text-transform:uppercase;letter-spacing:.08em;font-weight:500}
        .dl-val{font-size:.85rem;color:#1A1A1A}
        .dl-val.mono{font-family:'Courier New',monospace;font-size:.68rem;word-break:break-all}
        .sp-link{color:#E31E24;text-decoration:none;font-size:.82rem}
        .sp-link:hover{text-decoration:underline}
        .dl-summary,.dl-error{display:flex;flex-direction:column;gap:.5rem}
        .summary-text{font-size:.85rem;color:#1A1A1A;line-height:1.7;background:#f8f8f8;border-left:2px solid #E31E24;padding:.75rem 1rem;border-radius:0 2px 2px 0}
        .error-text{font-family:'Courier New',monospace;font-size:.72rem;color:#E31E24;background:#fff5f5;padding:.75rem;border-radius:2px}
        .dl-loading{font-size:.75rem;color:#7A7A7A;text-align:center;padding:.5rem}
      `}</style>
    </div>
  );
}

export default function JobHistory({ jobs, loading, msalInstance, accounts }) {
  if (loading && jobs.length === 0) return (
    <div className="he"><p>Cargando historial…</p>
    <style>{`.he{font-size:.75rem;color:#7A7A7A;text-align:center;padding:3rem;font-family:'DM Sans',sans-serif}`}</style></div>);

  if (jobs.length === 0) return (
    <div className="he">
      <div className="he-icon">—</div>
      <p>No hay transcripciones registradas.</p>
      <p>Lance su primera desde "Nueva transcripción".</p>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400&display=swap');
        .he{font-family:'DM Sans',sans-serif;font-size:.8rem;color:#7A7A7A;text-align:center;padding:4rem 2rem;display:flex;flex-direction:column;align-items:center;gap:.5rem;font-weight:300}
        .he-icon{font-family:'Playfair Display',serif;font-size:2rem;color:#e8e8e8;margin-bottom:.5rem}
      `}</style>
    </div>);

  return (
    <div className="hl">
      {jobs.map(job => <JobRow key={job.id} job={job} msalInstance={msalInstance} accounts={accounts}/>)}
      <style>{`.hl{display:flex;flex-direction:column;gap:.75rem;max-width:800px}`}</style>
    </div>);
}