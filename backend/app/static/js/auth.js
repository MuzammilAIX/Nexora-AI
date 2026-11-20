// Nexora AI — auth.js
// Login form → POST /api/v1/auth/login → store JWT → redirect to /app/index.html
// Exposes helpers: getToken(), getUser(), clearToken(), requireAuth()

const AUTH_API_BASE = "/api/v1";
const TOKEN_KEY = "nexora_token";
const USER_KEY  = "nexora_user";

function getToken()  { return localStorage.getItem(TOKEN_KEY); }
function getUser()   {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}
function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// Route guard — call from any authenticated page.
function requireAuth() {
  if (!getToken()) {
    window.location.href = "/app/login.html";
    throw new Error("no-token");
  }
}

// Login form handler (only runs on login.html)
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("login-form");
  if (!form) return;  // not the login page

  if (getToken()) {
    window.location.href = "/app/index.html";
    return;
  }

  const errEl = document.getElementById("login-error");
  const btn   = document.getElementById("login-btn");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errEl.classList.remove("show");
    btn.disabled = true;
    btn.textContent = "Signing in…";

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    try {
      const resp = await fetch(`${AUTH_API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(data.detail || `Login failed (${resp.status})`);
      }
      if (!data.access_token) {
        throw new Error("Login response missing access_token");
      }

      localStorage.setItem(TOKEN_KEY, data.access_token);
      if (data.user) {
        localStorage.setItem(USER_KEY, JSON.stringify(data.user));
      } else {
        try {
          const meResp = await fetch(`${AUTH_API_BASE}/auth/me`, {
            headers: { "Authorization": `Bearer ${data.access_token}` },
          });
          if (meResp.ok) {
            const me = await meResp.json();
            localStorage.setItem(USER_KEY, JSON.stringify(me));
          } else {
            localStorage.setItem(USER_KEY, JSON.stringify({ email }));
          }
        } catch {
          localStorage.setItem(USER_KEY, JSON.stringify({ email }));
        }
      }

      window.location.href = "/app/index.html";
    } catch (err) {
      errEl.textContent = err.message || "Login failed";
      errEl.classList.add("show");
      btn.disabled = false;
      btn.textContent = "Sign in";
    }
  });
});
