// Nexora AI - Activity page (Slice 1.8e)
// Read-only list of audit events from GET /api/v1/audit.
// No mutations, no modal, no user input.

const ACTIVITY_PATH = "/audit";

const ActivityState = {
  items: [],
  loading: false,
  inFlight: false,
  error: null,
};

async function fetchActivity(force) {
  if (ActivityState.inFlight && !force) return;
  ActivityState.inFlight = true;
  ActivityState.loading = true;
  ActivityState.error = null;
  renderActivityPage();

  try {
    const { ok, status, data } = await api.get(ACTIVITY_PATH);
    if (!ok) {
      ActivityState.error =
        "Failed to load activity: " +
        ((data && data.detail) || `HTTP ${status}`);
      ActivityState.items = [];
    } else {
      ActivityState.items = Array.isArray(data) ? data : [];
    }
  } catch (err) {
    ActivityState.error = "Failed to load activity: " + err.message;
    ActivityState.items = [];
  } finally {
    ActivityState.loading = false;
    ActivityState.inFlight = false;
  }
  renderActivityPage();
}

function _activityIcon(eventType) {
  if (!eventType) return "\u25CF";
  if (eventType.indexOf("approval") === 0)   return "\u2713";
  if (eventType.indexOf("integration") === 0) return "\u26A1";
  if (eventType.indexOf("run") === 0)         return "\u2699";
  if (eventType.indexOf("task") === 0)        return "\u25A1";
  if (eventType.indexOf("auth") === 0)        return "\u25C9";
  return "\u25CF";
}

function _activityPayloadSummary(payload) {
  if (!payload || typeof payload !== "object") return "";
  const keys = Object.keys(payload);
  if (!keys.length) return "";
  return keys.slice(0, 3).map(k => {
    const v = payload[k];
    const sv = v === null || v === undefined ? "\u2014" : String(v);
    return k + ": " + (sv.length > 40 ? sv.slice(0, 40) + "\u2026" : sv);
  }).join(" \u00B7 ");
}

function renderActivityPage() {
  const main = document.getElementById("app-main");
  if (!main) return;
  if (window.location.hash.replace(/^#\/?/, "") !== "activity") return;

  const refreshLabel = ActivityState.loading ? "Loading\u2026" : "Refresh";
  const refreshDisabled = ActivityState.loading ? "disabled" : "";

  main.innerHTML = `
    <div class="page-title">Activity</div>
    <div class="page-subtitle">Audit trail of agent operations and important business actions</div>
    ${ActivityState.error
      ? `<div class="toast error show" style="position:static;margin-bottom:16px;max-width:none;">${ActivityState.error}</div>`
      : ""}
    <div class="panel">
      <div class="panel-header">
        <span>Events (${ActivityState.items.length})</span>
        <button type="button" onclick="fetchActivity(true)" ${refreshDisabled}>${refreshLabel}</button>
      </div>
      <ul class="activity-list" id="activity-list"></ul>
    </div>
  `;

  const list = document.getElementById("activity-list");
  if (!ActivityState.items.length) {
    list.innerHTML = `
      <li class="empty-state">
        <h3>No activity yet</h3>
        Run a workflow from the Assistant page or connect an integration, and events will appear here.
      </li>`;
    return;
  }

  ActivityState.items.forEach((event) => {
    const li = document.createElement("li");
    li.className = "activity-row";

    const when = event.created_at
      ? new Date(event.created_at).toLocaleString()
      : "";
    const subject = event.subject_type
      ? `${event.subject_type}${event.subject_id ? " \u00B7 " + String(event.subject_id).slice(0, 8) : ""}`
      : "";
    const summary = _activityPayloadSummary(event.payload);

    li.innerHTML = `
      <div class="activity-icon">${_activityIcon(event.event_type)}</div>
      <div class="activity-body">
        <div class="activity-header">
          <span class="activity-event">${event.event_type || "event"}</span>
          <span class="activity-when">${when}</span>
        </div>
        ${subject ? `<div class="activity-subject">${subject}</div>` : ""}
        ${summary ? `<div class="activity-summary">${summary}</div>` : ""}
      </div>
    `;
    list.appendChild(li);
  });
}

window.addEventListener("page:show", (ev) => {
  if (ev.detail && ev.detail.page === "activity") {
    fetchActivity();
  }
});
