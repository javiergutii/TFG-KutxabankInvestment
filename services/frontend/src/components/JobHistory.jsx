import { useState } from "react";
import { getJobStatus } from "../lib/api";

const STATUS_CONFIG = {
  pending:    { label: "En cola",       color: "#718096", dot: "⬤" },
  running:    { label: "Procesando",    color: "#f6c90e", dot: "⬤" },
  done:       { label: "Completado",    color: "#00c896", dot: "⬤" },
  error:      { label: "Error",         color: "#fc5b5b", dot: "⬤" },
};

function formatDate(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleString("es-ES", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function JobRow({ job, msalInstance, accounts }) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;

  const handleExpand = async () => {
    if (!expanded && !detail) {
      setLoadingDetail(true);
      try {
        const data = await getJobStatus(msalInstance, accounts, job.id);
        setDetail(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoadingDetail(false);
      }
    }
    setExpanded((v) => !v);
  };

  return (
    <div className={`job-row ${expanded ? "expanded" : ""}`}>
      <div className="job-row-header" onClick={handleExpand}>
        <div className="job-status-dot" style={{ color: cfg.color }}>
          {cfg.dot}
        </div>
        <div className="job-info">
          <span className="job-empresa">{job.empresa || "Sin nombre"}</span>
          <span className="job-url">{job.url?.slice(0, 60)}…</span>
        </div>
        <div className="job-meta">
          <span className="job-status-label" style={{ color: cfg.color }}>
            {cfg.label}
          </span>
          <span className="job-date">{formatDate(job.created_at)}</span>
        </div>
        <span className="job-chevron">{expanded ? "▲" : "▼"}</span>
      </div>

      {expanded && (
        <div className="job-detail">
          {loadingDetail ? (
            <p className="detail-loading">Cargando detalles…</p>
          ) : detail ? (
            <>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Estado</span>
                  <span className="detail-value" style={{ color: cfg.color }}>{cfg.label}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Empresa</span>
                  <span className="detail-value">{detail.empresa}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Iniciado por</span>
                  <span className="detail-value">{detail.user_name || "—"}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">SharePoint</span>
                  <span className="detail-value">
                    {detail.sharepoint_url ? (
                      <a href={detail.sharepoint_url} target="_blank" rel="noreferrer" className="sp-link">
                        Ver archivo ↗
                      </a>
                    ) : "Pendiente"}
                  </span>
                </div>
              </div>

              {detail.url && (
                <div className="detail-item full-width">
                  <span className="detail-label">URL del webcast</span>
                  <span className="detail-value mono">{detail.url}</span>
                </div>
              )}

              {detail.resumen && (
                <div className="detail-summary">
                  <span className="detail-label">Resumen</span>
                  <p className="summary-text">{detail.resumen}</p>
                </div>
              )}

              {detail.error_msg && (
                <div className="detail-error">
                  <span className="detail-label">Error</span>
                  <p className="error-text">{detail.error_msg}</p>
                </div>
              )}
            </>
          ) : (
            <p className="detail-loading">No se pudieron cargar los detalles.</p>
          )}
        </div>
      )}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');

        .job-row {
          background: #0d1117;
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 10px;
          overflow: hidden;
          transition: border-color 0.15s;
        }

        .job-row:hover, .job-row.expanded {
          border-color: rgba(255,255,255,0.12);
        }

        .job-row-header {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem 1.25rem;
          cursor: pointer;
          user-select: none;
        }

        .job-status-dot {
          font-size: 0.5rem;
          flex-shrink: 0;
        }

        .job-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 0.2rem;
          min-width: 0;
        }

        .job-empresa {
          font-size: 0.9rem;
          font-weight: 600;
          color: #e2e8f0;
        }

        .job-url {
          font-family: 'Space Mono', monospace;
          font-size: 0.62rem;
          color: #4a5568;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .job-meta {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0.2rem;
          flex-shrink: 0;
        }

        .job-status-label {
          font-family: 'Space Mono', monospace;
          font-size: 0.68rem;
          font-weight: 700;
        }

        .job-date {
          font-family: 'Space Mono', monospace;
          font-size: 0.62rem;
          color: #4a5568;
        }

        .job-chevron {
          color: #4a5568;
          font-size: 0.6rem;
          flex-shrink: 0;
        }

        .job-detail {
          padding: 1.25rem;
          border-top: 1px solid rgba(255,255,255,0.05);
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 1rem;
        }

        .detail-item {
          display: flex;
          flex-direction: column;
          gap: 0.3rem;
        }

        .detail-item.full-width { grid-column: 1 / -1; }

        .detail-label {
          font-family: 'Space Mono', monospace;
          font-size: 0.6rem;
          color: #4a5568;
          text-transform: uppercase;
          letter-spacing: 0.1em;
        }

        .detail-value {
          font-size: 0.85rem;
          color: #e2e8f0;
        }

        .detail-value.mono {
          font-family: 'Space Mono', monospace;
          font-size: 0.65rem;
          word-break: break-all;
        }

        .sp-link {
          color: #00c896;
          text-decoration: none;
          font-size: 0.82rem;
        }

        .sp-link:hover { text-decoration: underline; }

        .detail-summary, .detail-error {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .summary-text {
          font-size: 0.85rem;
          color: #a0aec0;
          line-height: 1.7;
          background: rgba(255,255,255,0.02);
          border-left: 2px solid rgba(0,200,150,0.3);
          padding: 0.75rem 1rem;
          border-radius: 0 6px 6px 0;
        }

        .error-text {
          font-family: 'Space Mono', monospace;
          font-size: 0.72rem;
          color: #fc5b5b;
          background: rgba(252,91,91,0.05);
          padding: 0.75rem;
          border-radius: 6px;
        }

        .detail-loading {
          font-family: 'Space Mono', monospace;
          font-size: 0.72rem;
          color: #4a5568;
          text-align: center;
          padding: 0.5rem;
        }
      `}</style>
    </div>
  );
}

export default function JobHistory({ jobs, loading, msalInstance, accounts }) {
  if (loading && jobs.length === 0) {
    return (
      <div className="history-empty">
        <p>Cargando historial…</p>
        <style>{`.history-empty { font-family: 'Space Mono', monospace; font-size: 0.75rem; color: #4a5568; text-align: center; padding: 3rem; }`}</style>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="history-empty">
        <div className="empty-icon">◎</div>
        <p>Todavía no hay transcripciones.</p>
        <p>Lanza tu primera desde "Nueva transcripción".</p>
        <style>{`
          .history-empty { font-family: 'Space Mono', monospace; font-size: 0.72rem; color: #4a5568; text-align: center; padding: 4rem 2rem; display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
          .empty-icon { font-size: 2rem; color: #2d3748; margin-bottom: 0.5rem; }
        `}</style>
      </div>
    );
  }

  return (
    <div className="history-list">
      {jobs.map((job) => (
        <JobRow
          key={job.id}
          job={job}
          msalInstance={msalInstance}
          accounts={accounts}
        />
      ))}
      <style>{`.history-list { display: flex; flex-direction: column; gap: 0.75rem; max-width: 800px; }`}</style>
    </div>
  );
}