import { useState } from "react";
import { launchJob, inspectForm } from "../lib/api";

// Pasos del formulario
const STEP_URL    = "url";
const STEP_FIELDS = "fields";
const STEP_DONE   = "done";

export default function JobForm({ msalInstance, accounts, onJobLaunched }) {
  const [step, setStep]         = useState(STEP_URL);
  const [url, setUrl]           = useState("");
  const [empresa, setEmpresa]   = useState("");
  const [fields, setFields]     = useState([]);      // campos detectados por el scraping
  const [formData, setFormData] = useState({});      // valores que rellena el usuario
  const [status, setStatus]     = useState(null);    // null | 'loading' | 'error'
  const [errorMsg, setErrorMsg] = useState("");

  // ── Paso 1: obtener campos del formulario del webcast ─────────────────────
  const handleInspect = async () => {
    if (!url.trim()) {
      setErrorMsg("La URL del webcast es obligatoria");
      setStatus("error");
      return;
    }
    setStatus("loading");
    setErrorMsg("");
    try {
      const detected = await inspectForm(msalInstance, accounts, url.trim());
      // Si no detecta campos, mostramos al menos el campo email por defecto
      const result = detected.length > 0 ? detected : [
        { id: "email", label: "Email", field_type: "email", placeholder: "tu@empresa.com" }
      ];
      setFields(result);
      // Inicializar formData con los ids detectados
      const initial = {};
      result.forEach(f => { initial[f.id] = ""; });
      setFormData(initial);
      setStep(STEP_FIELDS);
    } catch (e) {
      setErrorMsg(e.message || "Error al inspeccionar el formulario");
      setStatus("error");
    } finally {
      setStatus(null);
    }
  };

  // ── Paso 2: lanzar transcripción con los datos rellenados ─────────────────
  const handleLaunch = async () => {
    setStatus("loading");
    setErrorMsg("");
    try {
      const job = await launchJob(msalInstance, accounts, {
        url: url.trim(),
        empresa: empresa.trim() || "Sin especificar",
        form_data: formData,
      });
      setStep(STEP_DONE);
      onJobLaunched(job);
    } catch (e) {
      setErrorMsg(e.message || "Error al lanzar el proceso");
      setStatus("error");
    } finally {
      setStatus(null);
    }
  };

  const handleReset = () => {
    setStep(STEP_URL);
    setUrl("");
    setEmpresa("");
    setFields([]);
    setFormData({});
    setStatus(null);
    setErrorMsg("");
  };

  const renderField = (f) => {
    const value = formData[f.id] || "";
    const onChange = (e) => setFormData(prev => ({ ...prev, [f.id]: e.target.value }));

    if (f.field_type === "select" && f.options?.length > 0) {
      return (
        <div className="field-group" key={f.id}>
          <label>{f.label}</label>
          <div className="select-wrap">
            <select value={value} onChange={onChange} className="field-input">
              <option value="">Selecciona…</option>
              {f.options.map(o => <option key={o} value={o}>{o}</option>)}
            </select>
            <span className="select-arrow">▾</span>
          </div>
        </div>
      );
    }

    if (f.field_type === "checkbox") {
      return (
        <div className="field-group field-group--check" key={f.id}>
          <input
            type="checkbox"
            id={f.id}
            checked={value === "true"}
            onChange={e => setFormData(prev => ({ ...prev, [f.id]: e.target.checked ? "true" : "false" }))}
          />
          <label htmlFor={f.id} style={{ textTransform: "none", fontSize: "0.85rem", color: "#e2e8f0" }}>
            {f.label}
          </label>
        </div>
      );
    }

    return (
      <div className="field-group" key={f.id}>
        <label>{f.label}</label>
        <input
          type={f.field_type === "email" ? "email" : "text"}
          value={value}
          onChange={onChange}
          placeholder={f.placeholder || `Introduce ${f.label.toLowerCase()}…`}
          className="field-input"
        />
      </div>
    );
  };

  return (
    <div className="job-form">

      {/* ── PASO 1: URL + Empresa ── */}
      <div className="form-section">
        <div className="section-label">01 — Webcast</div>
        <div className="field-group">
          <label>URL del webcast <span className="required">*</span></label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://edge.media-server.com/mmc/p/..."
            className="field-input mono"
            disabled={step === STEP_FIELDS}
          />
        </div>
        <div className="field-group">
          <label>Empresa / Emisor</label>
          <input
            type="text"
            value={empresa}
            onChange={(e) => setEmpresa(e.target.value)}
            placeholder="Nombre de la empresa que emite el webcast"
            className="field-input"
            disabled={step === STEP_FIELDS}
          />
        </div>

        {step === STEP_URL && (
          <button
            className="inspect-btn"
            onClick={handleInspect}
            disabled={status === "loading"}
          >
            {status === "loading"
              ? "⏳ Analizando formulario…"
              : "🔍 Obtener requisitos de acceso"}
          </button>
        )}

        {step === STEP_FIELDS && (
          <button className="reset-link" onClick={handleReset}>
            ← Cambiar URL
          </button>
        )}
      </div>

      {/* ── PASO 2: Campos detectados ── */}
      {step === STEP_FIELDS && (
        <div className="form-section">
          <div className="section-label">02 — Datos de acceso al webcast</div>
          <p className="section-note">
            {fields.length} campo(s) detectado(s) en el formulario de registro
          </p>

          <div className="fields-grid">
            {fields.map(renderField)}
          </div>
        </div>
      )}

      {/* Status */}
      {status === "error" && (
        <div className="status-bar error">❌ {errorMsg}</div>
      )}

      {/* Botón lanzar — solo en paso 2 */}
      {step === STEP_FIELDS && (
        <button
          className="submit-btn"
          onClick={handleLaunch}
          disabled={status === "loading"}
        >
          {status === "loading"
            ? "⏳ Lanzando proceso…"
            : "▶  Iniciar transcripción"}
        </button>
      )}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');

        .job-form {
          max-width: 680px;
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .form-section {
          background: #0d1117;
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 12px;
          padding: 1.75rem;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }

        .section-label {
          font-family: 'Space Mono', monospace;
          font-size: 0.65rem;
          font-weight: 700;
          color: #00c896;
          letter-spacing: 0.15em;
          text-transform: uppercase;
        }

        .section-note {
          font-family: 'Space Mono', monospace;
          font-size: 0.67rem;
          color: #4a5568;
          line-height: 1.6;
          margin-top: -0.5rem;
        }

        .fields-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
        }

        .field-group {
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
        }

        .field-group--check {
          flex-direction: row;
          align-items: center;
          gap: 0.6rem;
        }

        label {
          font-size: 0.75rem;
          font-weight: 600;
          color: #718096;
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .required { color: #00c896; }

        .field-input {
          background: #080a0f;
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 8px;
          color: #e2e8f0;
          font-family: 'Syne', sans-serif;
          font-size: 0.88rem;
          padding: 0.65rem 0.85rem;
          outline: none;
          transition: border-color 0.15s, box-shadow 0.15s;
          width: 100%;
        }

        .field-input.mono {
          font-family: 'Space Mono', monospace;
          font-size: 0.75rem;
        }

        .field-input:focus {
          border-color: rgba(0,200,150,0.4);
          box-shadow: 0 0 0 3px rgba(0,200,150,0.08);
        }

        .field-input:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .field-input::placeholder { color: #2d3748; }

        .select-wrap {
          position: relative;
        }

        select.field-input {
          appearance: none;
          padding-right: 2rem;
          cursor: pointer;
        }

        .select-arrow {
          position: absolute;
          right: 0.85rem;
          top: 50%;
          transform: translateY(-50%);
          color: #4a5568;
          pointer-events: none;
          font-size: 0.75rem;
        }

        .inspect-btn {
          padding: 0.85rem 1.5rem;
          background: transparent;
          color: #00c896;
          font-family: 'Space Mono', monospace;
          font-size: 0.78rem;
          font-weight: 700;
          letter-spacing: 0.06em;
          border: 1px solid rgba(0,200,150,0.3);
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.15s;
          align-self: flex-start;
        }

        .inspect-btn:hover:not(:disabled) {
          background: rgba(0,200,150,0.08);
          border-color: rgba(0,200,150,0.6);
        }

        .inspect-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .reset-link {
          background: transparent;
          border: none;
          color: #4a5568;
          font-family: 'Space Mono', monospace;
          font-size: 0.68rem;
          cursor: pointer;
          padding: 0;
          align-self: flex-start;
          transition: color 0.15s;
        }

        .reset-link:hover { color: #e2e8f0; }

        .status-bar {
          padding: 0.75rem 1rem;
          border-radius: 8px;
          font-family: 'Space Mono', monospace;
          font-size: 0.75rem;
        }

        .status-bar.error {
          background: rgba(252,91,91,0.08);
          border: 1px solid rgba(252,91,91,0.2);
          color: #fc5b5b;
        }

        .submit-btn {
          padding: 1rem 2rem;
          background: #00c896;
          color: #080a0f;
          font-family: 'Space Mono', monospace;
          font-size: 0.82rem;
          font-weight: 700;
          letter-spacing: 0.06em;
          border: none;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.15s;
          align-self: flex-start;
        }

        .submit-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 8px 24px rgba(0,200,150,0.25);
        }

        .submit-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}