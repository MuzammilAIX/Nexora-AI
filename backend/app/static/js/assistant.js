// Nexora AI - Assistant chat page (Slice 1.9)
// Chat UI over POST /api/v1/orchestrator/stream (SSE).
// Renders plan, intermediate events, and final state as structured assistant messages.

const AssistantState = {
  messages: [],       // [{role: "user"|"assistant", content: string|object, id, ts}]
  streaming: false,
  error: null,
};

let _assistantMsgCounter = 0;

function _assistantNewId() {
  _assistantMsgCounter += 1;
  return "m" + Date.now() + "-" + _assistantMsgCounter;
}

function _assistantNow() {
  return new Date().toLocaleTimeString();
}

// ---------------------------------------------------------------------------
// SSE reader - async generator that yields parsed JSON events
// ---------------------------------------------------------------------------
async function* _assistantReadSSE(response) {
  if (!response.body) throw new Error("No response body");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let frameEnd;
      while ((frameEnd = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, frameEnd);
        buffer = buffer.slice(frameEnd + 2);

        for (const line of frame.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (!payload) continue;
          try {
            yield JSON.parse(payload);
          } catch (e) {
            console.warn("[assistant] failed to parse SSE data:", e, payload.slice(0, 200));
          }
        }
      }
    }
  } finally {
    try { reader.releaseLock(); } catch (e) {}
  }
}

// ---------------------------------------------------------------------------
// Send message - streams response and updates assistant message in place
// ---------------------------------------------------------------------------
async function assistantSend(text) {
  if (AssistantState.streaming) return;
  const trimmed = (text || "").trim();
  if (!trimmed) return;

  // Append user message
  AssistantState.messages.push({
    id: _assistantNewId(),
    role: "user",
    content: trimmed,
    ts: _assistantNow(),
  });

  // Append empty assistant message that will fill in
  const assistantMsg = {
    id: _assistantNewId(),
    role: "assistant",
    content: "",
    ts: _assistantNow(),
    status: "streaming",
    events: [],   // accumulated intermediate events
    final: null,
    error: null,
  };
  AssistantState.messages.push(assistantMsg);

  AssistantState.streaming = true;
  AssistantState.error = null;
  renderAssistantPage();

  const token = localStorage.getItem("nexora_token");
  const url = "/api/v1/orchestrator/stream";

  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
        "Accept": "text/event-stream",
      },
      body: JSON.stringify({ user_request: trimmed }),
    });

    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      let detail = "";
      try { detail = JSON.parse(text).detail; } catch (e) {}
      throw new Error(
        "Request failed (HTTP " + resp.status + ")" + (detail ? ": " + JSON.stringify(detail) : "")
      );
    }

    for await (const event of _assistantReadSSE(resp)) {
      const type = event.type || "unknown";

      if (type === "final") {
        assistantMsg.final = event;
        assistantMsg.status = "done";
        // Extract a human-facing summary from event.state
        const state = event.state || {};
        assistantMsg.content =
          state.status === "pending_approval"
            ? "Your request is ready but requires approval before it can execute."
            : state.status === "completed"
            ? "Task completed."
            : state.status === "failed"
            ? "The task failed."
            : "Run finished with status: " + (state.status || "unknown");
        renderAssistantPage();
      } else if (type === "error") {
        assistantMsg.error = event.error || "Unknown error";
        assistantMsg.status = "error";
        renderAssistantPage();
      } else if (type === "end") {
        // Terminator - stop
        break;
      } else {
        // Any other event - append to intermediate event log
        assistantMsg.events.push(event);
        renderAssistantPage();
      }
    }

    if (assistantMsg.status === "streaming") {
      assistantMsg.status = "done";
      renderAssistantPage();
    }
  } catch (err) {
    console.error("[assistant] stream error", err);
    assistantMsg.status = "error";
    assistantMsg.error = err.message || String(err);
    renderAssistantPage();
  } finally {
    AssistantState.streaming = false;
    renderAssistantPage();
    // Refresh the pending approvals badge if a new approval was created
    if (typeof fetchOverviewData === "function") {
      try { fetchOverviewData(true); } catch (e) {}
    }
  }
}

// ---------------------------------------------------------------------------
// Rendering helpers
// ---------------------------------------------------------------------------
function _assistantEscape(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function _assistantRenderEventLog(events) {
  if (!events.length) return "";
  const recent = events.slice(-6);
  return `
    <details class="assistant-details" open>
      <summary>Activity (${events.length} event${events.length === 1 ? "" : "s"})</summary>
      <ul class="assistant-event-log">
        ${recent.map((e) => `
          <li>
            <span class="assistant-event-type">${_assistantEscape(e.type || "event")}</span>
            ${e.agent ? `<span class="assistant-event-detail"> · ${_assistantEscape(e.agent)}</span>` : ""}
            ${e.tool ? `<span class="assistant-event-detail"> · ${_assistantEscape(e.tool)}</span>` : ""}
            ${e.message ? `<span class="assistant-event-detail"> · ${_assistantEscape(e.message)}</span>` : ""}
          </li>`).join("")}
      </ul>
    </details>`;
}

function _assistantRenderFinal(final) {
  if (!final) return "";
  const state = final.state || {};
  const tasks = Array.isArray(state.tasks) ? state.tasks : [];
  const results = Array.isArray(state.task_results) ? state.task_results : [];
  const analysis = state.analysis || {};

  const approvalTasks = results.filter(
    (r) => r.status === "pending_approval" && r.approval_id
  );

  return `
    ${analysis.intent ? `<div class="assistant-intent"><strong>Intent:</strong> ${_assistantEscape(analysis.intent)}</div>` : ""}
    ${analysis.goal ? `<div class="assistant-goal"><strong>Goal:</strong> ${_assistantEscape(analysis.goal)}</div>` : ""}
    ${tasks.length ? `
      <div class="assistant-tasks">
        <div class="assistant-section-label">Plan (${tasks.length} task${tasks.length === 1 ? "" : "s"})</div>
        <ol>
          ${tasks.map((t) => {
            const res = results.find((r) => r.task_id === t.task_id) || {};
            const status = res.status || "pending";
            return `
              <li class="assistant-task assistant-task-${_assistantEscape(status)}">
                <div class="assistant-task-desc">${_assistantEscape(t.description)}</div>
                <div class="assistant-task-meta">
                  Agent: <strong>${_assistantEscape(t.agent_type || "?")}</strong>
                  · Status: <strong>${_assistantEscape(status)}</strong>
                  ${t.requires_approval ? " · ⚠ requires approval" : ""}
                </div>
                ${res.reason ? `<div class="assistant-task-reason">${_assistantEscape(res.reason)}</div>` : ""}
              </li>`;
          }).join("")}
        </ol>
      </div>` : ""}
    ${approvalTasks.length ? `
      <div class="assistant-approval-prompt">
        <div class="assistant-section-label">⚠ Approval required</div>
        <p>${approvalTasks.length} task${approvalTasks.length === 1 ? "" : "s"} waiting for your review.</p>
        <a href="#/approvals" class="assistant-approval-link">Go to Approvals →</a>
      </div>` : ""}
    <details class="assistant-details">
      <summary>Raw state (debug)</summary>
      <pre class="assistant-raw">${_assistantEscape(JSON.stringify(state, null, 2))}</pre>
    </details>
  `;
}

function _assistantRenderMessage(msg) {
  const roleClass = msg.role === "user" ? "assistant-msg-user" : "assistant-msg-assistant";
  const avatar = msg.role === "user" ? "T" : "N";
  const avatarClass = msg.role === "user" ? "assistant-avatar-user" : "assistant-avatar-assistant";

  let body = "";
  if (msg.role === "user") {
    body = `<div class="assistant-msg-text">${_assistantEscape(msg.content)}</div>`;
  } else {
    if (msg.status === "streaming") {
      body = `
        <div class="assistant-msg-text assistant-thinking">
          <span class="assistant-spinner"></span> Thinking…
          ${_assistantRenderEventLog(msg.events)}
        </div>`;
    } else if (msg.status === "error") {
      body = `
        <div class="assistant-msg-text assistant-error">
          <strong>Error:</strong> ${_assistantEscape(msg.error || "Unknown error")}
        </div>`;
    } else if (msg.final) {
      body = `
        <div class="assistant-msg-text">${_assistantEscape(msg.content)}</div>
        ${_assistantRenderEventLog(msg.events)}
        ${_assistantRenderFinal(msg.final)}
      `;
    } else {
      body = `<div class="assistant-msg-text">${_assistantEscape(msg.content || "(no response)")}</div>`;
    }
  }

  return `
    <div class="assistant-msg ${roleClass}">
      <div class="assistant-avatar ${avatarClass}">${avatar}</div>
      <div class="assistant-bubble">
        ${body}
        <div class="assistant-ts">${_assistantEscape(msg.ts || "")}</div>
      </div>
    </div>`;
}

function renderAssistantPage() {
  const main = document.getElementById("app-main");
  if (!main) return;
  if (window.location.hash.replace(/^#\/?/, "") !== "assistant") return;

  const sendDisabled = AssistantState.streaming ? "disabled" : "";

  main.innerHTML = `
    <div class="page-title">Assistant</div>
    <div class="page-subtitle">Ask Nexora to run a workflow</div>
    <div class="assistant-container">
      <div class="assistant-thread" id="assistant-thread">
        ${AssistantState.messages.length === 0 ? `
          <div class="assistant-empty">
            <h3>Ask Nexora to run a workflow</h3>
            <p>For example: "list my HubSpot leads", "prepare a monthly sales report", or "summarize open approvals".</p>
          </div>` : ""}
        ${AssistantState.messages.map(_assistantRenderMessage).join("")}
      </div>
      <form class="assistant-input-row" id="assistant-form">
        <textarea id="assistant-input" class="assistant-input" rows="2" placeholder="Ask Nexora to run a workflow…" ${sendDisabled}></textarea>
        <button type="submit" class="primary assistant-send" ${sendDisabled}>
          ${AssistantState.streaming ? "Running…" : "Send"}
        </button>
      </form>
    </div>
  `;

  const form = document.getElementById("assistant-form");
  const input = document.getElementById("assistant-input");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = input ? input.value : "";
      if (input) input.value = "";
      assistantSend(text);
    });
  }
  if (input && !AssistantState.streaming) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
      }
    });
    input.focus();
  }

  // Auto-scroll to bottom
  const thread = document.getElementById("assistant-thread");
  if (thread) thread.scrollTop = thread.scrollHeight;
}

window.addEventListener("page:show", (ev) => {
  if (ev.detail && ev.detail.page === "assistant") {
    renderAssistantPage();
  }
});
