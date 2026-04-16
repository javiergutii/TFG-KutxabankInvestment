import { useState } from "react";
import { launchJob, inspectForm } from "../lib/api";

const STEP_URL = "url", STEP_FIELDS = "fields";

export default function JobForm({ msalInstance, accounts, onJobLaunched }) {
  const [step, setStep] = useState(STEP_URL);
  const [url, setUrl] = useState("");
  const [empresa, setEmpresa] = useState("");
  const [year, setYear] = useState("");
  const [fields, setFields] = useState([]);
  const [formData, setFormData] = useState({});
  const [status, setStatus] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  // Genera las opciones de año: año actual hasta 5 años atrás
  const getYearOptions = () => {
    const current = new Date().getFullYear();
    const options = [];
    for (let y = current; y >= current - 5; y--) {
      options.push(y);
    }
    return options;
  };

  const handleInspect = async () => {
    if (!url.trim()) { setErrorMsg("La URL del webcast es obligatoria"); setStatus("error"); return; }
    if (!year) { setErrorMsg("El año de la conferencia es obligatorio"); setStatus("error"); return; }
    setStatus("loading"); setErrorMsg("");
    try {
      const detected = await inspectForm(msalInstance, accounts, url.trim());
      const result = detected.length > 0 ? detected : [{ id: "email", label: "Email", field_type: "email", placeholder: "tu@empresa.com" }];
      setFields(result);
      const initial = {}; result.forEach(f => { initial[f.id] = ""; }); setFormData(initial);
      setStep(STEP_FIELDS);
    } catch (e) { setErrorMsg(e.message || "Error al inspeccionar el formulario"); setStatus("error"); }
    finally { setStatus(null); }
  };

  const handleLaunch = async () => {
    setStatus("loading"); setErrorMsg("");
    try {
      const job = await launchJob(msalInstance, accounts, {
        url: url.trim(),
        empresa: empresa.trim() || "Sin especificar",
        year: year,
        form_data: formData,
      });
      onJobLaunched(job);
    } catch (e) { setErrorMsg(e.message || "Error al lanzar el proceso"); setStatus("error"); }
    finally { setStatus(null); }
  };

  const handleReset = () => {
    setStep(STEP_URL); setUrl(""); setEmpresa(""); setYear("");
    setFields([]); setFormData({}); setStatus(null); setErrorMsg("");
  };

  const renderField = (f) => {
    const value = formData[f.id] || "";
    const onChange = (e) => setFormData(prev => ({ ...prev, [f.id]: e.target.value }));
    if (f.field_type === "select" && f.options?.length > 0) return (
      <div className="fg" key={f.id}><label>{f.label}{f.required && <span className="req"> *</span>}</label>
        <div className="sw"><select value={value} onChange={onChange} className="fi"><option value="">Seleccione…</option>{f.options.map(o=><option key={o} value={o}>{o}</option>)}</select><span className="sa">▾</span></div></div>);
    if (f.field_type === "checkbox") return (
      <div className="fg fc" key={f.id}><input type="checkbox" id={f.id} checked={value==="true"} onChange={e=>setFormData(p=>({...p,[f.id]:e.target.checked?"true":"false"}))} className="cb"/>
        <label htmlFor={f.id} className="cl">{f.label}</label></div>);
    return (<div className="fg" key={f.id}><label>{f.label}{f.required&&<span className="req"> *</span>}</label>
      <input type={f.field_type==="email"?"email":"text"} value={value} onChange={onChange} placeholder={f.placeholder||""} className="fi"/></div>);
  };

  return (
    <div className="jf">
      <div className="fc-card">
        <div className="ch"><div className="sn">01</div><div><h3 className="ct">Datos del webcast</h3><p className="cd">Introduce la URL, el nombre de la empresa y el año de la conferencia</p></div></div>
        <div className="cb-body">
          <div className="fg"><label>URL del webcast <span className="req">*</span></label>
            <input type="url" value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://edge.media-server.com/mmc/p/..." className="fi mono" disabled={step===STEP_FIELDS}/></div>
          <div className="fg-2col">
            <div className="fg"><label>Empresa / Emisor</label>
              <input type="text" value={empresa} onChange={e=>setEmpresa(e.target.value)} placeholder="Nombre de la empresa" className="fi" disabled={step===STEP_FIELDS}/></div>
            <div className="fg"><label>Año de la conferencia <span className="req">*</span></label>
              <div className="sw">
                <select value={year} onChange={e=>setYear(e.target.value)} className="fi" disabled={step===STEP_FIELDS}>
                  <option value="">Seleccione año…</option>
                  {getYearOptions().map(y => <option key={y} value={String(y)}>{y}</option>)}
                </select>
                <span className="sa">▾</span>
              </div>
            </div>
          </div>
          {step===STEP_URL && <button className="bi" onClick={handleInspect} disabled={status==="loading"}>{status==="loading"?"Analizando…":"Obtener requisitos de acceso →"}</button>}
          {step===STEP_FIELDS && <button className="bb" onClick={handleReset}>← Cambiar URL</button>}
        </div>
      </div>

      {step===STEP_FIELDS && (
        <div className="fc-card">
          <div className="ch"><div className="sn">02</div><div><h3 className="ct">Datos de acceso al webcast</h3><p className="cd">{fields.length} campo(s) detectado(s) — rellene los datos de registro</p></div></div>
          <div className="cb-body"><div className="fg-grid">{fields.map(renderField)}</div></div>
        </div>)}

      {status==="error" && <div className="se"><span className="sd"/>{errorMsg}</div>}

      {step===STEP_FIELDS && (
        <div className="fa">
          <button className="bl" onClick={handleLaunch} disabled={status==="loading"}>{status==="loading"?"Procesando…":"Iniciar transcripción"}</button>
          <p className="an">El proceso se ejecutará en segundo plano. Puede seguir el estado en Historial.</p>
        </div>)}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=DM+Sans:wght@300;400;500&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        .jf{max-width:700px;display:flex;flex-direction:column;gap:1.5rem;font-family:'DM Sans',sans-serif}
        .fc-card{background:#fff;border:1px solid #e8e8e8;border-top:2px solid #E31E24;border-radius:2px}
        .ch{display:flex;align-items:flex-start;gap:1.25rem;padding:1.5rem 1.75rem;border-bottom:1px solid #f0f0f0}
        .sn{font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:600;color:#E31E24;line-height:1;flex-shrink:0;padding-top:2px}
        .ct{font-family:'Playfair Display',serif;font-size:1rem;font-weight:600;color:#1A1A1A;margin-bottom:.2rem}
        .cd{font-size:.78rem;color:#7A7A7A;font-weight:300}
        .cb-body{padding:1.75rem;display:flex;flex-direction:column;gap:1.25rem}
        .fg-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.25rem}
        .fg-2col{display:grid;grid-template-columns:1fr 1fr;gap:1.25rem}
        .fg{display:flex;flex-direction:column;gap:.4rem}
        .fc{flex-direction:row;align-items:center;gap:.6rem}
        label{font-size:.72rem;font-weight:500;color:#1A1A1A;text-transform:uppercase;letter-spacing:.07em}
        .req{color:#E31E24}
        .fi{background:#fff;border:1px solid #d8d8d8;border-radius:2px;color:#1A1A1A;font-family:'DM Sans',sans-serif;font-size:.88rem;padding:.65rem .85rem;outline:none;transition:border-color .15s;width:100%}
        .fi.mono{font-family:'Courier New',monospace;font-size:.78rem}
        .fi:focus{border-color:#E31E24;box-shadow:0 0 0 2px rgba(227,30,36,.08)}
        .fi:disabled{background:#f8f8f8;color:#7A7A7A;cursor:not-allowed}
        .fi::placeholder{color:#c0c0c0}
        .sw{position:relative} select.fi{appearance:none;padding-right:2rem;cursor:pointer}
        .sa{position:absolute;right:.85rem;top:50%;transform:translateY(-50%);color:#7A7A7A;pointer-events:none;font-size:.75rem}
        .cb{accent-color:#E31E24;width:14px;height:14px;cursor:pointer}
        .cl{font-size:.85rem;text-transform:none;letter-spacing:0;font-weight:400;color:#1A1A1A}
        .bi{align-self:flex-start;padding:.7rem 1.5rem;background:#1A1A1A;color:#fff;font-family:'DM Sans',sans-serif;font-size:.82rem;font-weight:500;border:none;border-radius:2px;cursor:pointer;transition:all .15s}
        .bi:hover:not(:disabled){background:#E31E24;box-shadow:0 4px 12px rgba(227,30,36,.2)}
        .bi:disabled{opacity:.5;cursor:not-allowed}
        .bb{background:transparent;border:none;color:#7A7A7A;font-family:'DM Sans',sans-serif;font-size:.78rem;cursor:pointer;padding:0;transition:color .15s;align-self:flex-start}
        .bb:hover{color:#1A1A1A}
        .se{display:flex;align-items:center;gap:.6rem;padding:.85rem 1.25rem;background:#fff5f5;border:1px solid #ffd0d0;border-left:3px solid #E31E24;border-radius:2px;font-size:.82rem;color:#c41a1f}
        .sd{width:6px;height:6px;border-radius:50%;background:#E31E24;flex-shrink:0}
        .fa{display:flex;align-items:center;gap:1.5rem}
        .bl{padding:.85rem 2rem;background:#E31E24;color:#fff;font-family:'DM Sans',sans-serif;font-size:.88rem;font-weight:500;border:none;border-radius:2px;cursor:pointer;transition:all .15s;white-space:nowrap}
        .bl:hover:not(:disabled){background:#c41a1f;box-shadow:0 4px 16px rgba(227,30,36,.3)}
        .bl:disabled{opacity:.5;cursor:not-allowed}
        .an{font-size:.75rem;color:#7A7A7A;font-weight:300;line-height:1.5}
      `}</style>
    </div>
  );
}