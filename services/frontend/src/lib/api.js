// ============================================================
// api.js — Llamadas al backend Python con token Microsoft
// ============================================================

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function getAuthHeaders(msalInstance, accounts) {
  const { loginRequest } = await import("../authConfig");
  const response = await msalInstance.acquireTokenSilent({
    ...loginRequest,
    account: accounts[0],
  });
  return {
    Authorization: `Bearer ${response.accessToken}`,
    "Content-Type": "application/json",
  };
}

export async function launchJob(msalInstance, accounts, payload) {
  const headers = await getAuthHeaders(msalInstance, accounts);
  const res = await fetch(`${API_BASE}/api/jobs`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getJobs(msalInstance, accounts) {
  const headers = await getAuthHeaders(msalInstance, accounts);
  const res = await fetch(`${API_BASE}/api/jobs`, { headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getJobStatus(msalInstance, accounts, jobId) {
  const headers = await getAuthHeaders(msalInstance, accounts);
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`, { headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}