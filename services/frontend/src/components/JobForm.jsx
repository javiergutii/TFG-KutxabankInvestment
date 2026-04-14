import { useState } from "react";
import { launchJob } from "../lib/api";

const FIELD_TEMPLATES = [
  { id: "email", label: "Email de registro", type: "email", placeholder: "tu@empresa.com", required: true },
  { id: "nombre", label: "Nombre", type: "text", placeholder: "Tu nombre completo", required: false },
  { id: "apellidos", label: "Apellidos", type: "text", placeholder: "Tus apellidos", required: false },
  { id: "empresa", label: "Empresa", type: "text", placeholder: "Nombre de tu empresa", required: false },
];

export default function JobForm({ msalInstance, accounts, onJobLaunched }) {
  const [url, setUrl] = useState("");
  const [empresa, setEmpresa] = useState("");
  const [formFields, setFormFields] = useState({ email: "", nombre: "", apellidos: "", empresa_webcast: "" });
  const [extraFields, setExtraFields] = useState([]);
  const [status, setStatus] = useState(null); // null | 'loading' | 'success' | 'error'
  const [errorMsg, setErrorMsg] = useState("");

  const handleFieldChange = (id, value) => {
    setFormFields((prev) => ({ ...prev, [id]: value }));
  };

  const addExtraField = () => {
    setExtraFields((prev) => [...prev, { id: `extra_${Date.now()}`, label: "", value: "" }]);
  };

  const removeExtraField = (id) => {
    setExtraFields((prev) => prev.filter((f) => f.id !== id));
  };

  const handleSubmit = async () => {
    if (!url.trim()) {
      setErrorMsg("La URL del webcast es obligatoria");
      setStatus("error");
      return;
    }

    const allFormData = {
      ...formFields,
      ...Object.fromEntries(extraFields.map((f) => [f.label || f.id, f.value])),
    };

    setStatus("loading");
    setErrorMsg("");

    try {
      const job = await launchJob(msalInstance, accounts, {
        url: url.trim(),
        empresa: empresa.trim() || "Sin especificar",
        form_data: allFormData,
      });
      setStatus("success");
      onJobLaunched(job);
      // Reset form
      setUrl("");
      setEmpresa("");
      setFormFields({ email: "", nombre: "", apellidos: "", empresa_webcast: "" });
      setExtraFields([]);
    } catch (e) {
      setStatus("error");
      setErrorMsg(e.message || "Error desconocido al lanzar el proceso");
    }
  };

  return (
    <div className="job-form">
      {/* Sección 1: Info del proceso */}
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
          />
        </div>
      </div>

      {/* Sección 2: Datos del formulario de acceso */}
      <div className="form-section">
        <div className="section-label">02 — Datos de acceso al webcast</div>
        <p className="section-note">
          Estos datos se usarán para rellenar automáticamente el formulario de registro del webcast
        </p>
        <div className="fields-grid">
          {FIELD_TEMPLATES.map((f) => (
            <div className="field-group" key={f.id}>
              <label>
                {f.label}
                {f.required && <span className="required"> *</span>}
              </label>
              <input
                type={f.type}
                value={formFields[f.id] || ""}
                onChange={(e) => handleFieldChange(f.id, e.target.value)}
                placeholder={f.placeholder}
                className="field-input"
              />
            </div>
          ))}
        </div>

        {/* Campos extra */}
        {extraFields.map((f) => (
          <div className="extra-field" key={f.id}>
            <input
              type="text"
              value={f.label}
              onChange={(e) =>
                setExtraFields((prev) =>
                  prev.map((ef) => (ef.id === f.id ? { ...ef, label: e.target.value } : ef))
                )
              }
              placeholder="Nombre del campo"
              className="field-input extra-label-input"
            />
            <input
              type="text"
              value={f.value}
              onChange={(e) =>
                setExtraFields((prev) =>
                  prev.map((ef) => (ef.id === f.id ? { ...ef, value: e.target.value } : ef))
                )
              }
              placeholder="Valor"
              className="field-input"
            />
            <button className="remove-btn" onClick={() => removeExtraField(f.id)}>✕</button>
          </div>
        ))}

        <button className="add-field-btn" onClick={addExtraField}>
          + Añadir campo extra
        </button>
      </div>

      {/* Status */}
      {status === "error" && (
        <div className="status-bar error">❌ {errorMsg}</div>
      )}
      {status === "success" && (
        <div className="status-bar success">✅ Proceso lanzado. Puedes seguir el estado en el Historial.</div>
      )}

      {/* Submit */}
      <button
        className="submit-btn"
        onClick={handleSubmit}
        disabled={status === "loading"}
      >
        {status === "loading" ? (
          <span className="loading-text">⏳ Lanzando proceso…</span>
        ) : (
          "▶  Iniciar transcripción"
        )}
      </button>

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

        .field-input::placeholder { color: #2d3748; }

        .extra-field {
          display: flex;
          gap: 0.5rem;
          align-items: center;
        }

        .extra-label-input { flex: 0 0 160px; }

        .remove-btn {
          background: transparent;
          border: 1px solid rgba(255,255,255,0.07);
          color: #4a5568;
          border-radius: 6px;
          width: 32px;
          height: 32px;
          cursor: pointer;
          font-size: 0.75rem;
          flex-shrink: 0;
          transition: all 0.15s;
        }

        .remove-btn:hover { color: #fc5b5b; border-color: rgba(252,91,91,0.3); }

        .add-field-btn {
          font-family: 'Space Mono', monospace;
          font-size: 0.7rem;
          color: #4a5568;
          background: transparent;
          border: 1px dashed rgba(255,255,255,0.08);
          padding: 0.5rem 1rem;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.15s;
          align-self: flex-start;
        }

        .add-field-btn:hover {
          color: #00c896;
          border-color: rgba(0,200,150,0.3);
        }

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

        .status-bar.success {
          background: rgba(0,200,150,0.08);
          border: 1px solid rgba(0,200,150,0.2);
          color: #00c896;
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