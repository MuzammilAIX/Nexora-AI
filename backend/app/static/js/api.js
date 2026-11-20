// Nexora AI - shared API client
const API_BASE = "/api/v1";

async function _request(method, path, body) {
  const token = localStorage.getItem("nexora_token");
  const headers = { "Accept": "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = "Bearer " + token;
  let resp;
  try {
    resp = await fetch(API_BASE + path, {
      method: method,
      headers: headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    return { ok: false, status: 0, data: { detail: "Network error: " + err.message } };
  }
  let data = null;
  const text = await resp.text();
  if (text) {
    try { data = JSON.parse(text); } catch (e) { data = text; }
  }
  if (resp.status === 401) {
    localStorage.removeItem("nexora_token");
    localStorage.removeItem("nexora_user");
    if (window.location.pathname.indexOf("/login.html") === -1) {
      window.location.href = "/app/login.html";
    }
  }
  return { ok: resp.ok, status: resp.status, data: data };
}

const api = {
  get:  function(path)       { return _request("GET",    path); },
  post: function(path, body) { return _request("POST",   path, body || {}); },
  del:  function(path)       { return _request("DELETE", path); },
};