// Nexora AI — layout shell + hash router (Slice 1.8b)
// Wires the sidebar nav to content panels. Each page is a placeholder
// for now; subsequent slices replace the placeholder with real content.

const PAGES = [
  { key: "overview",     label: "Overview",     icon: "▦",  subtitle: "Business KPIs and recent automation" },
  { key: "assistant",    label: "Assistant",    icon: "✦",  subtitle: "Ask Nexora to run a workflow" },
  { key: "approvals",    label: "Approvals",    icon: "✓",  subtitle: "Pending actions awaiting human review" },
  { key: "integrations", label: "Integrations", icon: "⚡", subtitle: "Connected external services" },
  { key: "activity",     label: "Activity",     icon: "◉",  subtitle: "Audit trail of agent operations" },
];

function _initials(email) {
  if (!email) return "?";
  const name = email.split("@")[0];
  const parts = name.split(/[._-]/);
  return parts.map(p => p[0]).join("").slice(0, 2).toUpperCase();
}

function _renderSidebar() {
  const html = PAGES.map(p => `
    <li>
      <a href="#/${p.key}" data-page="${p.key}">
        <span class="icon">${p.icon}</span>
        <span>${p.label}</span>
      </a>
    </li>`).join("");
  document.getElementById("app-nav").innerHTML = html;
}

function _setActive(pageKey) {
  document.querySelectorAll(".app-nav a").forEach(a => {
    a.classList.toggle("active", a.dataset.page === pageKey);
  });
}

function _renderHeader() {
  const u = getUser() || {};
  const email = u.email || "user";
  const init = _initials(email);

  document.getElementById("header-user").innerHTML = `
    <span class="avatar" title="${email}"
          style="display:inline-flex;align-items:center;justify-content:center;
                 width:28px;height:28px;border-radius:50%;
                 background:var(--accent);color:#0f1115;
                 font-weight:700;font-size:12px;">${init}</span>
    <span class="email">${email}</span>
    <button type="button" onclick="clearToken(); window.location.href='/app/login.html'">Sign out</button>
  `;
}

function _renderPage(pageKey) {
  const page = PAGES.find(p => p.key === pageKey) || PAGES[0];
  _setActive(page.key);

  const main = document.getElementById("app-main");
  main.innerHTML = `
    <div class="page-title">${page.label}</div>
    <div class="page-subtitle">${page.subtitle}</div>
    <div class="placeholder-card">
      <h3>${page.label} — coming in a later slice</h3>
      <p>This page will be wired up after the shell is in place.</p>
    </div>
  `;

  // Dispatch a custom event so page-specific scripts (approvals.js, etc.)
  // can hook in when their page is shown. Right now nothing listens.
  window.dispatchEvent(new CustomEvent("page:show", { detail: { page: page.key } }));
}

function _currentPageFromHash() {
  const hash = (window.location.hash || "").replace(/^#\/?/, "");
  return PAGES.some(p => p.key === hash) ? hash : PAGES[0].key;
}

function _router() {
  _renderPage(_currentPageFromHash());
}

// Entry point — called from index.html after requireAuth().
function initLayout() {
  _renderSidebar();
  _renderHeader();
  _router();
  window.addEventListener("hashchange", _router);
}
