// Nexora AI - Integrations page (Slice 1.8d)
// Lists connected integrations, supports HubSpot connect via modal,
// and disconnect with confirmation.
// Uses unique top-level names (IntegrationsState, INTEGRATIONS_PATH) to
// avoid colliding with other page scripts.

const INTEGRATIONS_PATH = "/integrations";

const IntegrationsState = {
  items: [],
  loading: false,
  inFlight: false,
  error: null,
  modalOpen: false,
  modalSubmitting: false,
  modalError: null,
};

// ---------------------------------------------------------------------------
// Toast (same contract as approvals.js - idempotent if both run)
// ---------------------------------------------------------------------------
function showIntegrationsToast(message, kind) {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.className = "toast " + (kind || "success") + " show";
  el.textContent = message;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), 5000);
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------
async function fetchIntegrations(force) {
  if (IntegrationsState.inFlight && !force) return;
  IntegrationsState.inFlight = true;
  IntegrationsState.loading = true;
  IntegrationsState.error = null;
  renderIntegrationsPage();

  try {
    const { ok, status, data } = await api.get(INTEGRATIONS_PATH);
    if (!ok) {
      IntegrationsState.error =
        "Failed to load integrations: " +
        ((data && data.detail) || `HTTP ${status}`);
      IntegrationsState.items = [];
    } else {
      IntegrationsState.items = Array.isArray(data) ? data : [];
    }
  } catch (err) {
    IntegrationsState.error = "Failed to load integrations: " + err.message;
    IntegrationsState.items = [];
  } finally {
    IntegrationsState.loading = false;
    IntegrationsState.inFlight = false;
  }
  renderIntegrationsPage();
}

// ---------------------------------------------------------------------------
// Connect modal
// ---------------------------------------------------------------------------
function openConnectModal() {
  IntegrationsState.modalOpen = true;
  IntegrationsState.modalError = null;
  IntegrationsState.modalSubmitting = false;
  renderIntegrationsPage();
}

function closeConnectModal() {
  IntegrationsState.modalOpen = false;
  IntegrationsState.modalError = null;
  IntegrationsState.modalSubmitting = false;
  renderIntegrationsPage();
}

async function submitConnect() {
  const input = document.getElementById("hubspot-key-input");
  const key = input ? input.value.trim() : "";
  if (!key) {
    IntegrationsState.modalError = "Service Key is required.";
    renderIntegrationsPage();
    return;
  }
  IntegrationsState.modalSubmitting = true;
  IntegrationsState.modalError = null;
  renderIntegrationsPage();

  try {
    const { ok, status, data } = await api.post("/integrations/hubspot/connect", {
      access_token: key,
    });
    if (!ok) {
      IntegrationsState.modalError =
        "Connect failed: " + ((data && data.detail) || `HTTP ${status}`);
      IntegrationsState.modalSubmitting = false;
      renderIntegrationsPage();
      return;
    }
    showIntegrationsToast("HubSpot connected.", "success");
    IntegrationsState.modalOpen = false;
    IntegrationsState.modalSubmitting = false;
    await fetchIntegrations(true);
  } catch (err) {
    IntegrationsState.modalError = "Connect failed: " + err.message;
    IntegrationsState.modalSubmitting = false;
    renderIntegrationsPage();
  }
}

// ---------------------------------------------------------------------------
// Disconnect
// ---------------------------------------------------------------------------
async function disconnectIntegration(id, label) {
  if (!window.confirm(`Disconnect ${label || "this integration"}? This cannot be undone.`)) {
    return;
  }
  try {
    const { ok, status, data } = await api.del(`/integrations/${id}`);
    if (!ok) {
      showIntegrationsToast(
        "Disconnect failed: " + ((data && data.detail) || `HTTP ${status}`),
        "error"
      );
      return;
    }
    showIntegrationsToast("Disconnected.", "success");
    await fetchIntegrations(true);
  } catch (err) {
    showIntegrationsToast("Disconnect failed: " + err.message, "error");
  }
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------
function renderIntegrationsPage() {
  const main = document.getElementById("app-main");
  if (!main) return;
  if (window.location.hash.replace(/^#\/?/, "") !== "integrations") return;

  const refreshLabel = IntegrationsState.loading ? "Loading…" : "Refresh";
  const refreshDisabled = IntegrationsState.loading ? "disabled" : "";

  main.innerHTML = `
    <div class="page-title">Integrations</div>
    <div class="page-subtitle">Connect external services so agents can act on your behalf</div>
    ${IntegrationsState.error
      ? `<div class="toast error show" style="position:static;margin-bottom:16px;max-width:none;">${IntegrationsState.error}</div>`
      : ""}
    <div class="panel">
      <div class="panel-header">
        <span>Connected (${IntegrationsState.items.length})</span>
        <div style="display:flex;gap:8px;">
          <button type="button" class="primary" onclick="openConnectModal()">Connect HubSpot</button>
          <button type="button" onclick="fetchIntegrations(true)" ${refreshDisabled}>${refreshLabel}</button>
        </div>
      </div>
      <ul class="integration-list" id="integration-list"></ul>
    </div>
    ${IntegrationsState.modalOpen ? renderConnectModal() : ""}
  `;

  const list = document.getElementById("integration-list");
  if (!IntegrationsState.items.length) {
    list.innerHTML = `
      <li class="empty-state">
        <h3>No integrations connected</h3>
        Click "Connect HubSpot" to add one.
      </li>`;
  } else {
    IntegrationsState.items.forEach((item) => {
      const li = document.createElement("li");
      li.className = "integration-row";
      const label =
        item.integration_type ||
        item.provider ||
        item.name ||
        item.type ||
        "integration";
      const status = item.status || "connected";
      const connected = item.connected_at
        ? new Date(item.connected_at).toLocaleString()
        : "";
      li.innerHTML = `
        <div class="integration-info">
          <div class="integration-name"><strong>${label}</strong></div>
          <div class="integration-meta">
            Status: <span class="status-${status}">${status}</span>
            ${connected ? " · Connected " + connected : ""}
          </div>
        </div>
        <button type="button" class="danger" onclick="disconnectIntegration('${item.id}', '${label}')">
          Disconnect
        </button>
      `;
      list.appendChild(li);
    });
  }
}

function renderConnectModal() {
  const submitting = IntegrationsState.modalSubmitting;
  const disabled = submitting ? "disabled" : "";
  return `
    <div class="modal-overlay" onclick="if(event.target===this) closeConnectModal()">
      <div class="modal">
        <div class="modal-header">
          <h2>Connect HubSpot</h2>
          <button type="button" class="modal-close" onclick="closeConnectModal()">×</button>
        </div>
        <div class="modal-body">
          <p>Paste your HubSpot Service Key below. It will be securely stored and used by the Sales Agent to read and update CRM data.</p>
          <label for="hubspot-key-input">Service Key</label>
          <input type="password" id="hubspot-key-input" placeholder="pat-..." autocomplete="off" ${disabled}>
          ${IntegrationsState.modalError
            ? `<div class="modal-error">${IntegrationsState.modalError}</div>`
            : ""}
        </div>
        <div class="modal-footer">
          <button type="button" onclick="closeConnectModal()" ${disabled}>Cancel</button>
          <button type="button" class="primary" onclick="submitConnect()" ${disabled}>
            ${submitting ? "Connecting…" : "Connect"}
          </button>
        </div>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------
window.addEventListener("page:show", (ev) => {
  if (ev.detail && ev.detail.page === "integrations") {
    fetchIntegrations();
  }
});
