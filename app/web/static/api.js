// Cliente de la API local. Los errores llegan como {error:{code,detail,params}}.
export class ApiError extends Error {
  constructor(code, detail = "", params = {}, status = 0) {
    super(code);
    this.code = code; this.detail = detail; this.params = params; this.status = status;
  }
}

async function request(method, url, body) {
  const opts = { method, headers: {} };
  if (body instanceof FormData) opts.body = body;
  else if (body !== undefined) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  let res;
  try { res = await fetch(url, opts); } catch { throw new ApiError("network"); }
  if (!res.ok) {
    let data = null;
    try { data = await res.json(); } catch { /* sin cuerpo JSON */ }
    const e = data?.error;
    if (e) throw new ApiError(e.code, e.detail, e.params, res.status);
    if (res.status === 422) throw new ApiError("unexpected", "datos no válidos", {}, 422);
    throw new ApiError("unexpected", `HTTP ${res.status}`, {}, res.status);
  }
  const type = res.headers.get("content-type") || "";
  if (type.includes("application/json")) return res.json();
  return res.blob();
}

const q = encodeURIComponent;
export const api = {
  system: () => request("GET", "api/system"),
  voices: (lang) => request("GET", `api/voices?lang=${q(lang)}`),
  installVoice: (id) => request("POST", `api/voices/${q(id)}/install`),
  installStatus: (id) => request("GET", `api/voices/${q(id)}/install`),
  sample: (id, body) => request("POST", `api/voices/${q(id)}/sample`, body),
  demo: (lang) => request("POST", `api/jobs/demo?lang=${q(lang)}`),
  upload: (file, lang, token) => { const f = new FormData(); f.append("file", file); f.append("language", lang); f.append("token", token); return request("POST", "api/jobs", f); },
  uploadProgress: (token) => request("GET", `api/uploads/${q(token)}`),
  jobs: () => request("GET", "api/jobs"),
  job: (id) => request("GET", `api/jobs/${q(id)}`),
  deleteJob: (id) => request("DELETE", `api/jobs/${q(id)}`),
  saveBook: (id, book) => request("PUT", `api/jobs/${q(id)}/book`, book),
  saveSettings: (id, s) => request("PUT", `api/jobs/${q(id)}/settings`, s),
  estimate: (id) => request("GET", `api/jobs/${q(id)}/estimate`),
  start: (id) => request("POST", `api/jobs/${q(id)}/start`),
  pause: (id) => request("POST", `api/jobs/${q(id)}/pause`),
  cancel: (id) => request("POST", `api/jobs/${q(id)}/cancel`),
  progress: (id) => request("GET", `api/jobs/${q(id)}/progress`),
  preview: (id, ch) => request("GET", `api/jobs/${q(id)}/chapters/${ch}/preview`),
  setCover: (id, file) => { const f = new FormData(); f.append("file", file); return request("POST", `api/jobs/${q(id)}/cover`, f); },
  coverUrl: (id) => `api/jobs/${q(id)}/cover?t=${Date.now()}`,
  startExport: (id, formats) => request("POST", `api/jobs/${q(id)}/export`, { formats }),
  exportStatus: (id) => request("GET", `api/jobs/${q(id)}/export`),
  downloadUrl: (id, name) => `api/jobs/${q(id)}/download/${q(name)}`,
};
