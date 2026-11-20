// Nexora AI - Overview dashboard (Slice 1.10)
// Reads existing endpoints in parallel: approvals, integrations, audit, runs.
// Renders KPI cards + recent activity lists with quick links.

const OverviewState = {
  loading: false,
  inFlight: false,
  error: null,
  approvals: [],
  integrations: [],
  audit: [],
  runs: [],
  lastFetched: null,
};

function _overviewIsToday(iso) {
  if (!iso) return false;
  const d = new Date(iso);
  const now = new Date();
  return d.getFullYear() === now.getFullYear() &&
         d.getMonth() === now.getMonth() &&
         d.getDate() === now.getDate();
}

function _overviewSuccessRate(runs) {
  if (!runs.length) return null;
  const completed = runs.filter(r => r.status === "completed").length;
  return Math.round((completed / runs.length) * 100);
}

function _overviewFmtTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString();
}

function _overviewShortRequest(text) {
  if (!text) return "(no request)";
  const t = String(text).replace(/\s+/g, " ").trim();
  return t.length > 80 ? t.slice(0, 80) + "\u2026" : t;
}

function _overviewStatusClass(status) {
  const s = String(status || "").toLowerCase();
  if (s.indexOf("complete") === 0) return "status-connected";
  if (s.indexOf("pending") === 0) return "status-pending";
  if (s.indexOf("fail") === 0 || s.indexOf("error") === 0) return "status-error";
  return "";
}

async function fetchOverviewData(force) {
  if (OverviewState.inFlight && !force) return;
  OverviewState.inFlight = true;
  OverviewState.loading = true;
  OverviewState.error = null;
  renderOverviewPage();

  const results = await Promise.allSettled([
    api.get("/approvals?status=pending"),
    api.get("/integrations"),
    api.get("/audit"),
    api.get("/orchestrator/runs"),
  ]);

  const [a, i, u, r] = results;

  OverviewState.approvals   = (a.status === "fulfilled" && a.value.ok && Array.isArray(a.value.data))   ? a.value.data   : [];
  OverviewState.integrations= (i.status === "fulfilled" && i.value.ok && Array.isArray(i.value.data))   ? i.value.data   : [];
  OverviewState.audit       = (u.status === "fulfilled" && u.value.ok && Array.isArray(u.value.data))   ? u.value.data   : [];
  OverviewState.runs        = (r.status === "fulfilled" && r.value.ok && Array.isArray(r.value.data))   ? r.value.data   : [];

  const failures = results.filter(x => x.status === "rejected" || (x.status === "fulfilled" && !x.value.ok));
  if (failures.length) {
    OverviewState.error = `Some data could not be loaded (${failures.length} of 4 endpoints failed).`;
  }

  OverviewState.lastFetched = new Date();
  OverviewState.loading = false;
  OverviewState.inFlight = false;
  renderOverviewPage();
}

function _overviewKpiCard(label, value, sublabel, href) {
  return `
    <a href="${href}" class="overview-kpi">
      <div class="overview-kpi-value">${value}</div>
      <div class="overview-kpi-label">${label}</div>
      <div class="overview-kpi-sub">${sublabel}</div>
    </a>
  `;
}

function renderOverviewPage() {
  const main = document.getElementById("app-main");
  if (!main) return;
  if (window.location.hash.replace(/^#\/?/, "") !== "overview") return;

  const refreshLabel = OverviewState.loading ? "Loading\u2026" : "Refresh";
  const refreshDisabled = OverviewState.loading ? "disabled" : "";

  const todayRuns = OverviewState.runs.filter(r => _overviewIsToday(r.created_at));
  const successRate = _overviewSuccessRate(OverviewState.runs);

  const recentRuns = OverviewState.runs.slice(0, 5);
  const recentApprovals = OverviewState.approvals.slice(0, 5);
  const recentActivity = OverviewState.audit.slice(0, 5);

  main.innerHTML = `
    <div class="page-title">Overview</div>
    <div class="page-subtitle">Business KPIs and recent automation</div>
    ${OverviewState.error
      ? `<div class="toast error show" style="position:static;margin-bottom:16px;max-width:none;">${OverviewState.error}</div>`
      : ""}
    <div class="overview-toolbar">
      <span class="overview-fetched">
        ${OverviewState.lastFetched ? "Last updated " + OverviewState.lastFetched.toLocaleTimeString() : ""}
      </span>
      <button type="button" onclick="fetchOverviewData(true)" ${refreshDisabled}>${refreshLabel}</button>
    </div>

    <div class="overview-kpis">
      ${_overviewKpiCard(
        "Pending approvals",
        OverviewState.approvals.length,
        "Awaiting review",
        "#/approvals"
      )}
      ${_overviewKpiCard(
        "Connected integrations",
        OverviewState.integrations.length,
        "Active services",
        "#/integrations"
      )}
      ${_overviewKpiCard(
        "Runs today",
        todayRuns.length,
        `of ${OverviewState.runs.length} total`,
        "#/activity"
      )}
      ${_overviewKpiCard(
        "Run success rate",
        successRate === null ? "\u2014" : successRate + "%",
        "Completed / total",
        "#/activity"
      )}
    </div>

    <div class="overview-grid">
      <div class="panel">
        <div class="panel-header">
          <span>Recent runs</span>
          <a href="#/activity">View all \u2192</a>
        </div>
        <ul class="overview-recent-list">
          ${
            recentRuns.length
              ? recentRuns.map(r => `
                  <li class="overview-recent-row">
                    <div class="overview-recent-main">
                      <div class="overview-recent-title">${_overviewShortRequest(r.user_request)}</div>
                      <div class="overview-recent-meta">
                        <span class="${_overviewStatusClass(r.status)}">${r.status}</span>
                        \u00B7 ${_overviewFmtTime(r.created_at)}
                      </div>
                    </div>
                  </li>`).join("")
              : `<li class="empty-state"><h3>No runs yet</h3>Start a workflow from the Assistant page.</li>`
          }
        </ul>
      </div>

      <div class="panel">
        <div class="panel-header">
          <span>Pending approvals</span>
          <a href="#/approvals">View all \u2192</a>
        </div>
        <ul class="overview-recent-list">
          ${
            recentApprovals.length
              ? recentApprovals.map(a => `
                  <li class="overview-recent-row">
                    <div class="overview-recent-main">
                      <div class="overview-recent-title">${a.agent_type || "agent"} \u00B7 ${a.task_id || ""}</div>
                      <div class="overview-recent-meta">${a.reason || ""}</div>
                    </div>
                  </li>`).join("")
              : `<li class="empty-state"><h3>Nothing pending</h3>No approvals waiting for review.</li>`
          }
        </ul>
      </div>

      <div class="panel overview-panel-wide">
        <div class="panel-header">
          <span>Recent activity</span>
          <a href="#/activity">View all \u2192</a>
        </div>
        <ul class="overview-recent-list">
          ${
            recentActivity.length
              ? recentActivity.map(e => `
                  <li class="overview-recent-row">
                    <div class="overview-recent-main">
                      <div class="overview-recent-title">${e.event_type || "event"}</div>
                      <div class="overview-recent-meta">
                        ${e.subject_type || ""}${e.subject_id ? " \u00B7 " + String(e.subject_id).slice(0, 8) : ""}
                        \u00B7 ${_overviewFmtTime(e.created_at)}
                      </div>
                    </div>
                  </li>`).join("")
              : `<li class="empty-state"><h3>No activity yet</h3>Events will appear here.</li>`
          }
        </ul>
      </div>
    </div>
  `;
}

window.addEventListener("page:show", (ev) => {
  if (ev.detail && ev.detail.page === "overview") {
    fetchOverviewData();
  }
});
