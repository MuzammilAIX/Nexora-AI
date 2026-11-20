// Nexora AI — Approvals page (Slice 1.8c, hardened)
// Wires: list fetch, row select, detail fetch, approve / reject actions.
// Listens for the "page:show" event dispatched by layout.js.

const ApprovalsState = {
  items: [],
  selectedId: null,
  detail: null,
  loading: false,
  inFlight: false,        // guard against double-fetch
  error: null,
};

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------
function showToast(message, kind) {
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
async function fetchApprovalsList(force) {
  if (ApprovalsState.inFlight && !force) {
    console.log("[approvals] fetch already in flight, skipping");
    return;
  }
  console.log("[approvals] fetching list...");
  ApprovalsState.inFlight = true;
  ApprovalsState.loading = true;
  ApprovalsState.error = null;
  renderApprovalsPage();

  try {
    const { ok, status, data } = await api.get("/approvals?status=pending");
    console.log("[approvals] response", status, data);
    if (!ok) {
      ApprovalsState.error =
        "Failed to load approvals: " +
        ((data && data.detail) || `HTTP ${status}`);
      ApprovalsState.items = [];
    } else {
      ApprovalsState.items = Array.isArray(data) ? data : [];
    }
  } catch (err) {
    console.error("[approvals] fetch threw", err);
    ApprovalsState.error = "Failed to load approvals: " + err.message;
    ApprovalsState.items = [];
  } finally {
    ApprovalsState.loading = false;
    ApprovalsState.inFlight = false;
  }

  if (
    ApprovalsState.selectedId &&
    !ApprovalsState.items.some((a) => a.id === ApprovalsState.selectedId)
  ) {
    ApprovalsState.selectedId = null;
    ApprovalsState.detail = null;
  }
  renderApprovalsPage();
}

async function selectApproval(id) {
  console.log("[approvals] selecting", id);
  ApprovalsState.selectedId = id;
  ApprovalsState.detail = null;
  renderApprovalsPage();
  try {
    const { ok, status, data } = await api.get(`/approvals/${id}`);
    console.log("[approvals] detail response", status, data);
    if (!ok) {
      showToast(
        "Failed to load approval detail: " +
          ((data && data.detail) || `HTTP ${status}`),
        "error"
      );
      return;
    }
    ApprovalsState.detail = data;
    renderApprovalsPage();
  } catch (err) {
    console.error("[approvals] detail threw", err);
    showToast("Failed to load approval detail: " + err.message, "error");
  }
}

async function approveSelected() {
  const id = ApprovalsState.selectedId;
  if (!id) return;
  const btn = document.getElementById("btn-approve");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Approving…";
  }
  try {
    const { ok, status, data } = await api.post(`/approvals/${id}/approve`, {});
    if (!ok) {
      showToast(
        "Approve failed: " + ((data && data.detail) || `HTTP ${status}`),
        "error"
      );
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Approve";
      }
      return;
    }
    const created =
      data &&
      data.execution_result &&
      data.execution_result.result &&
      data.execution_result.result.tasks_created;
    const createdMsg =
      Array.isArray(created) && created.length
        ? ` Created tasks: ${created.join(", ")}.`
        : "";
    showToast("Approved." + createdMsg, "success");
    ApprovalsState.selectedId = null;
    ApprovalsState.detail = null;
    await fetchApprovalsList(true);
  } catch (err) {
    console.error("[approvals] approve threw", err);
    showToast("Approve failed: " + err.message, "error");
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Approve";
    }
  }
}

async function rejectSelected() {
  const id = ApprovalsState.selectedId;
  if (!id) return;
  const reason = window.prompt(
    "Reason for rejection (optional):",
    "Rejected by reviewer"
  );
  if (reason === null) return;

  const btn = document.getElementById("btn-reject");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Rejecting…";
  }
  try {
    const { ok, status, data } = await api.post(`/approvals/${id}/reject`, {
      reason,
    });
    if (!ok) {
      showToast(
        "Reject failed: " + ((data && data.detail) || `HTTP ${status}`),
        "error"
      );
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Reject";
      }
      return;
    }
    showToast("Rejected.", "success");
    ApprovalsState.selectedId = null;
    ApprovalsState.detail = null;
    await fetchApprovalsList(true);
  } catch (err) {
    console.error("[approvals] reject threw", err);
    showToast("Reject failed: " + err.message, "error");
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Reject";
    }
  }
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------
function renderApprovalsPage() {
  const main = document.getElementById("app-main");
  if (!main) return;
  if (window.location.hash.replace(/^#\/?/, "") !== "approvals") return;

  const refreshLabel = ApprovalsState.loading ? "Loading…" : "Refresh";
  const refreshDisabled = ApprovalsState.loading ? "disabled" : "";

  main.innerHTML = `
    <div class="page-title">Approvals</div>
    <div class="page-subtitle">Pending actions awaiting human review</div>
    ${
      ApprovalsState.error
        ? `<div class="toast error show" style="position:static;margin-bottom:16px;max-width:none;">${ApprovalsState.error}</div>`
        : ""
    }
    <div class="approvals-grid">
      <div class="panel">
        <div class="panel-header">
          <span>Pending (${ApprovalsState.items.length})</span>
          <button type="button" onclick="fetchApprovalsList(true)" ${refreshDisabled}>
            ${refreshLabel}
          </button>
        </div>
        <ul class="approval-list" id="approval-list"></ul>
      </div>
      <div class="panel" id="approval-detail-panel"></div>
    </div>
  `;

  const list = document.getElementById("approval-list");
  if (!ApprovalsState.items.length) {
    list.innerHTML = `
      <li class="empty-state">
        <h3>No pending approvals</h3>
        Trigger a new run from the Assistant page or the API, and pending approvals will appear here.
      </li>`;
  } else {
    ApprovalsState.items.forEach((item) => {
      const li = document.createElement("li");
      li.className =
        "approval-row" +
        (item.id === ApprovalsState.selectedId ? " active" : "");
      li.onclick = () => selectApproval(item.id);
      const when = item.created_at
        ? new Date(item.created_at).toLocaleString()
        : "";
      li.innerHTML = `
        <div class="meta">
          <span class="agent">${item.agent_type}</span>
          <span>${when}</span>
        </div>
        <div class="reason">${item.reason || ""}</div>
        <div class="desc" title="${item.task_description || ""}">${
        item.task_description || ""
      }</div>
      `;
      list.appendChild(li);
    });
  }

  const detailPanel = document.getElementById("approval-detail-panel");
  if (!ApprovalsState.selectedId) {
    detailPanel.innerHTML = `
      <div class="empty-state">
        <h3>Select an approval</h3>
        Click a row on the left to review the proposed action.
      </div>`;
    return;
  }
  if (!ApprovalsState.detail) {
    detailPanel.innerHTML = `<div class="empty-state">Loading detail…</div>`;
    return;
  }

  const d = ApprovalsState.detail;
  const ctx = (d.proposed_action && d.proposed_action.context_preview) || {};
  const analysis = ctx.analysis || {};
  const reqs = Array.isArray(analysis.requirements) ? analysis.requirements : [];
  const cons = Array.isArray(analysis.constraints) ? analysis.constraints : [];

  detailPanel.innerHTML = `
    <div class="approval-detail">
      <h2>${d.agent_type || "Agent"} · task ${d.task_id || ""}</h2>
      <div class="subtitle">
        Status: <strong>${d.status || "pending"}</strong>
        · Created ${d.created_at ? new Date(d.created_at).toLocaleString() : ""}
      </div>
      <div class="detail-section">
        <div class="label">Reason for approval</div>
        <div class="value">${d.reason || "—"}</div>
      </div>
      <div class="detail-section">
        <div class="label">Proposed action</div>
        <div class="value">${d.task_description || "—"}</div>
      </div>
      ${
        ctx.user_request
          ? `<div class="detail-section"><div class="label">Original user request</div><div class="value">${ctx.user_request}</div></div>`
          : ""
      }
      ${
        analysis.intent
          ? `<div class="detail-section"><div class="label">Intent</div><div class="value">${analysis.intent}</div></div>`
          : ""
      }
      ${
        analysis.goal
          ? `<div class="detail-section"><div class="label">Goal</div><div class="value">${analysis.goal}</div></div>`
          : ""
      }
      ${
        reqs.length
          ? `<div class="detail-section"><div class="label">Requirements</div><ul>${reqs
              .map((r) => `<li>${r}</li>`)
              .join("")}</ul></div>`
          : ""
      }
      ${
        cons.length
          ? `<div class="detail-section"><div class="label">Constraints</div><ul>${cons
              .map((c) => `<li>${c}</li>`)
              .join("")}</ul></div>`
          : ""
      }
      <div class="detail-actions">
        <button type="button" class="primary" id="btn-approve" onclick="approveSelected()">Approve</button>
        <button type="button" class="danger" id="btn-reject" onclick="rejectSelected()">Reject</button>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Lifecycle — hook into layout router
// ---------------------------------------------------------------------------
window.addEventListener("page:show", (ev) => {
  if (ev.detail && ev.detail.page === "approvals") {
    fetchApprovalsList();
  }
});
