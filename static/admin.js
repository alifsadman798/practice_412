const $ = (selector) => document.querySelector(selector);
const status = $("#admin-status");

const definitions = {
  "bus-schedules": {
    label: "Bus Schedules & Fares",
    endpoint: "/api/admin/bus-schedules",
    key: "id",
    fields: [
      ["route_id", "Route ID", "text"],
      ["from_district", "From District", "text"],
      ["to_district", "To District", "text"],
      ["transport_name", "Transport / Company", "text"],
      ["departure", "Departure Time", "time"],
      ["arrival", "Arrival Time", "time"],
      ["fare", "Fare (BDT)", "number"],
    ],
  },
  "train-services": {
    label: "Train Services",
    endpoint: "/api/admin/train-services",
    key: "id",
    fields: [
      ["train_no", "Train Number", "text"],
      ["train_name", "Train Name", "text"],
      ["from_district", "Origin District", "text"],
      ["to_district", "Destination District", "text"],
      ["off_day", "Off Day (e.g. Monday/No off)", "text"],
      ["departure", "Departure Time", "time"],
      ["arrival", "Arrival Time", "time"],
      ["day_offset", "Arrival Day Offset", "number"],
    ],
  },
  "train-stops": {
    label: "Train Stops & Halts",
    endpoint: "/api/admin/train-stops",
    key: "id",
    fields: [
      ["train_no", "Train Number", "text"],
      ["train_name", "Train Name", "text"],
      ["stop_order", "Stop Order", "number"],
      ["station", "Station Name", "text"],
      ["district_name", "District", "text"],
      ["arrival", "Arrival Time", "time"],
      ["departure", "Departure Time", "time"],
      ["day_offset", "Day Offset", "number"],
      ["cumulative_km", "Cumulative KM", "number"],
    ],
  },
};

let authorization = "";
let editingKey = null;
let currentRows = [];

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function getModeBadge(mode, size = 12, interactive = true) {
  const m = String(mode || "").toLowerCase().trim();
  const interactiveCls = interactive ? " interactive" : "";
  if (m === "bus" || m.includes("bus")) {
    return `<span class="mode-icon-badge bus${interactiveCls}" title="Inter-District Bus"><svg class="mode-svg" viewBox="0 0 24 24" width="${size}" height="${size}" fill="currentColor" aria-hidden="true"><path d="M4 16c0 .88.39 1.67 1 2.22V20a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1v-1h8v1a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm9 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm-9.5-6V6h10v5h-10z"/></svg></span>`;
  }
  if (m === "train" || m.includes("train") || m.includes("rail")) {
    return `<span class="mode-icon-badge train${interactiveCls}" title="Bangladesh Railway"><svg class="mode-svg" viewBox="0 0 24 24" width="${size}" height="${size}" fill="currentColor" aria-hidden="true"><path d="M12 2c-4 0-8 .5-8 4v9.5C4 17.43 5.57 19 7.5 19L6 20.5v.5h12v-.5L16.5 19c1.93 0 3.5-1.57 3.5-3.5V6c0-3.5-4-4-8-4zM7.5 17c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm4.5-5H6V6h6v6zm4.5 5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-5h-5V6h5v6z"/></svg></span>`;
  }
  if (m === "local" || m === "road") {
    return `<span class="mode-icon-badge local${interactiveCls}" title="Local Transport"><svg class="mode-svg" viewBox="0 0 24 24" width="${size}" height="${size}" fill="currentColor" aria-hidden="true"><path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.22.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.85 7h10.29l1.04 3H5.81l1.04-3zM19 17H5v-4.66l.12-.34h13.77l.11.34V17z"/><circle cx="7.5" cy="14.5" r="1.5"/><circle cx="16.5" cy="14.5" r="1.5"/></svg></span>`;
  }
  if (m === "multimodal") {
    return `<span class="mode-icon-badge multimodal${interactiveCls}" title="Multimodal Journey"><span style="display:inline-flex;align-items:center;gap:3px;"><svg class="mode-svg" viewBox="0 0 24 24" width="11" height="11" fill="currentColor"><path d="M4 16c0 .88.39 1.67 1 2.22V20a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1v-1h8v1a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm9 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm-9.5-6V6h10v5h-10z"/></svg>+<svg class="mode-svg" viewBox="0 0 24 24" width="11" height="11" fill="currentColor"><path d="M12 2c-4 0-8 .5-8 4v9.5C4 17.43 5.57 19 7.5 19L6 20.5v.5h12v-.5L16.5 19c1.93 0 3.5-1.57 3.5-3.5V6c0-3.5-4-4-8-4zM7.5 17c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm4.5-5H6V6h6v6zm4.5 5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-5h-5V6h5v6z"/></svg></span></span>`;
  }
  return "";
}

function show(message, type = "info") {
  if (!message) {
    status.textContent = "";
    status.className = "status";
    return;
  }
  status.textContent = message;
  status.className = `status ${type}`;
}

async function request(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { Authorization: authorization, "Content-Type": "application/json", ...options.headers },
  });
  const value = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new Error(value?.detail || `Request failed (${response.status})`);
  return value;
}

// Modal Helpers
function openModal(modalId) {
  const modal = $(`#${modalId}`);
  if (modal) modal.classList.remove("hidden");
}

function closeModal(modalId) {
  const modal = $(`#${modalId}`);
  if (modal) modal.classList.add("hidden");
}

document.querySelectorAll("[data-close]").forEach((btn) => {
  btn.addEventListener("click", () => closeModal(btn.dataset.close));
});

document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) closeModal(backdrop.id);
  });
});

// -------------------------------------------------------------
// Mobile Sidebar Drawer & Responsive Navigation
// -------------------------------------------------------------

const mobileSidebarToggle = $("#mobile-sidebar-toggle");
const sidebarCloseBtn = $("#sidebar-close-btn");
const sidebarBackdrop = $("#sidebar-backdrop");
const appSidebar = $("#app-sidebar");

function openMobileSidebar() {
  if (appSidebar) appSidebar.classList.add("open");
  if (sidebarBackdrop) sidebarBackdrop.classList.add("active");
  document.body.classList.add("sidebar-open");
}

function closeMobileSidebar() {
  if (appSidebar) appSidebar.classList.remove("open");
  if (sidebarBackdrop) sidebarBackdrop.classList.remove("active");
  document.body.classList.remove("sidebar-open");
}

mobileSidebarToggle?.addEventListener("click", openMobileSidebar);
sidebarCloseBtn?.addEventListener("click", closeMobileSidebar);
sidebarBackdrop?.addEventListener("click", closeMobileSidebar);

document.querySelectorAll(".sidebar-nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    if (window.innerWidth <= 900) {
      closeMobileSidebar();
    }
  });
});

// -------------------------------------------------------------
// Admin Workspace Tab Switcher
// -------------------------------------------------------------

document.querySelectorAll("[data-admin-tab]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("[data-admin-tab]").forEach((b) => b.classList.toggle("active", b === btn));
    const tab = btn.dataset.adminTab;
    document.querySelectorAll(".admin-tab-pane").forEach((pane) => {
      pane.classList.toggle("hidden", pane.id !== `tab-pane-${tab}`);
    });

    if (tab === "overview") loadAdminOverview();
    if (tab === "records") loadEntity();
    if (tab === "disruptions") loadAdminDisruptions();
    if (tab === "reports") loadAdminReports();
    if (tab === "users") loadAdminUsers();
    if (tab === "audit") loadAuditLogs();
  });
});

// Quick action tab switchers
document.querySelectorAll("[data-goto-tab]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const targetTab = btn.dataset.gotoTab;
    const tabBtn = document.querySelector(`[data-admin-tab="${targetTab}"]`);
    if (tabBtn) tabBtn.click();
  });
});

$("#overview-refresh-btn")?.addEventListener("click", () => {
  loadAdminOverview();
});

$("#overview-quick-create-disruption")?.addEventListener("click", () => {
  openCreateDisruptionModal();
});

// -------------------------------------------------------------
// Admin Overview Dashboard (Live Metrics from PostgreSQL)
// -------------------------------------------------------------

async function loadAdminOverview() {
  try {
    const [disruptionsRes, reportsRes, usersRes, schedulesRes, logsRes] = await Promise.allSettled([
      request("/api/admin/disruptions?include_deleted=false"),
      request("/api/admin/reports?include_deleted=false"),
      request("/api/admin/users"),
      request("/api/admin/bus-schedules"),
      request("/api/admin/audit-logs"),
    ]);

    // Active Disruptions KPI & Sidebar Badge
    if (disruptionsRes.status === "fulfilled" && Array.isArray(disruptionsRes.value)) {
      const activeCount = disruptionsRes.value.filter((d) => (d.status || "").toUpperCase() === "ACTIVE").length;
      const kpiActive = $("#kpi-active-disruptions");
      if (kpiActive) kpiActive.textContent = activeCount;
      const kpiDisSub = $("#kpi-disruptions-sub");
      if (kpiDisSub) kpiDisSub.textContent = `${activeCount} live incident${activeCount === 1 ? "" : "s"}`;

      const disBadge = $("#sidebar-disruptions-badge");
      if (disBadge) {
        disBadge.textContent = activeCount;
        disBadge.classList.toggle("hidden", activeCount === 0);
      }
    }

    // Pending Reports KPI & Sidebar Badge
    if (reportsRes.status === "fulfilled" && Array.isArray(reportsRes.value)) {
      const pendingCount = reportsRes.value.filter((r) => (r.status || "").toUpperCase() === "PENDING").length;
      const kpiReports = $("#kpi-pending-reports");
      if (kpiReports) kpiReports.textContent = pendingCount;
      const kpiRepSub = $("#kpi-reports-sub");
      if (kpiRepSub) kpiRepSub.textContent = `${pendingCount} awaiting resolution`;

      const repBadge = $("#sidebar-reports-badge");
      if (repBadge) {
        repBadge.textContent = pendingCount;
        repBadge.classList.toggle("hidden", pendingCount === 0);
      }
    }

    // Users KPI
    if (usersRes.status === "fulfilled" && Array.isArray(usersRes.value)) {
      const totalUsers = usersRes.value.length;
      const blockedCount = usersRes.value.filter((u) => u.is_blocked || u.status === "blocked").length;
      const kpiUsers = $("#kpi-total-users");
      if (kpiUsers) kpiUsers.textContent = totalUsers;
      const kpiUsersSub = $("#kpi-users-sub");
      if (kpiUsersSub) kpiUsersSub.textContent = `${blockedCount} suspended / blocked`;
    }

    // Bus Schedules Count
    if (schedulesRes.status === "fulfilled" && Array.isArray(schedulesRes.value)) {
      const totalSchedules = schedulesRes.value.length;
      const kpiRecords = $("#kpi-transit-records");
      if (kpiRecords) kpiRecords.textContent = totalSchedules;
    }

    // Recent Administrative Activity
    const auditContainer = $("#overview-recent-audit");
    if (auditContainer) {
      if (logsRes.status === "fulfilled" && Array.isArray(logsRes.value) && logsRes.value.length > 0) {
        const recentLogs = logsRes.value.slice(0, 5);
        auditContainer.innerHTML = recentLogs.map((l) => {
          const time = l.created_at ? l.created_at.replace("T", " ").slice(0, 16) : "Recent";
          const action = escapeHtml(l.action || "UPDATE");
          const actor = escapeHtml(l.actor || "admin");
          const target = escapeHtml(l.target_type || "RECORD");
          const targetId = l.target_id ? ` #${escapeHtml(l.target_id)}` : "";
          return `
            <div class="overview-audit-item">
              <div class="audit-item-meta">
                <span class="audit-badge">${action}</span>
                <span class="audit-time">${time}</span>
              </div>
              <div><strong>${actor}</strong> modified ${target}${targetId}</div>
            </div>
          `;
        }).join("");
      } else {
        auditContainer.innerHTML = `<div style="padding: 14px; text-align: center; color: var(--secondary-text); font-size: 0.85rem;">No recent administrative activity recorded yet.</div>`;
      }
    }
  } catch (err) {
    console.warn("Failed to load admin overview metrics:", err);
  }
}

// -------------------------------------------------------------
// 2. User Issue Reports Management
// -------------------------------------------------------------

let currentAdminReports = [];
let activeReviewReport = null;

async function loadAdminReports() {
  const container = $("#admin-reports-table");
  if (!container) return;
  container.innerHTML = "<p style='padding:20px;'>Loading user reports...</p>";

  const statusVal = $("#admin-report-filter-status")?.value || "all";
  const catVal = $("#admin-report-filter-cat")?.value || "all";
  const searchVal = $("#admin-report-search")?.value.trim() || "";
  const includeDeleted = $("#admin-report-include-deleted")?.checked || false;

  const params = new URLSearchParams();
  if (statusVal && statusVal !== "all") params.append("status", statusVal);
  if (catVal && catVal !== "all") params.append("category", catVal);
  if (searchVal) params.append("search", searchVal);
  if (includeDeleted) params.append("include_deleted", "true");

  try {
    const reports = await request(`/api/admin/reports?${params.toString()}`);
    currentAdminReports = reports;

    const pendingCount = reports.filter((r) => (r.status || "").toUpperCase() === "PENDING" && !r.admin_deleted).length;
    const repBadge = $("#sidebar-reports-badge");
    if (repBadge) {
      repBadge.textContent = pendingCount;
      repBadge.classList.toggle("hidden", pendingCount === 0);
    }

    if (!reports.length) {
      container.innerHTML = "<p style='padding:20px; color:var(--text-muted);'>No user reports found matching your criteria.</p>";
      return;
    }

    const rows = reports.map((r) => {
      const statusCls = String(r.status || "PENDING").toLowerCase();
      const userDisplay = r.user_full_name ? `${escapeHtml(r.user_full_name)} (${escapeHtml(r.user_id)})` : escapeHtml(r.user_id);
      const isDeleted = r.admin_deleted || r.user_deleted;
      const deletedTag = isDeleted ? '<span class="status-pill rejected" style="font-size:0.65rem; margin-left:4px;">Deleted</span>' : '';

      return `
        <tr style="${isDeleted ? 'opacity: 0.65;' : ''}">
          <td><strong>${escapeHtml(r.report_id)}</strong>${deletedTag}</td>
          <td>${userDisplay}</td>
          <td><span class="pill small">${escapeHtml(r.category)}</span></td>
          <td style="max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(r.title)}">${escapeHtml(r.title)}</td>
          <td>${getModeBadge(r.transport_mode, 12)} ${escapeHtml(r.transport_mode || 'General')}</td>
          <td><span class="status-pill ${statusCls}">${escapeHtml(r.status)}</span></td>
          <td>${new Date(r.submitted_at).toLocaleDateString()}</td>
          <td style="white-space:nowrap;">
            <button class="button primary small" style="height:28px; padding:0 10px; font-size:0.8rem;" data-review-report="${escapeHtml(r.report_id)}">
              Review
            </button>
            ${!r.admin_deleted ? `
              <button class="button danger small" style="height:28px; padding:0 8px; font-size:0.8rem; margin-left:4px;" data-soft-delete-report="${escapeHtml(r.report_id)}" title="Soft delete from admin view">
                🗑️
              </button>
            ` : ''}
          </td>
        </tr>
      `;
    }).join("");

    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Report ID</th>
            <th>Reporting User</th>
            <th>Category</th>
            <th>Title</th>
            <th>Mode</th>
            <th>Status</th>
            <th>Date</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;

    container.querySelectorAll("[data-review-report]").forEach((btn) => {
      btn.addEventListener("click", () => openAdminReportModal(btn.dataset.reviewReport));
    });

    container.querySelectorAll("[data-soft-delete-report]").forEach((btn) => {
      btn.addEventListener("click", () => deleteAdminReport(btn.dataset.softDeleteReport));
    });
  } catch (error) {
    container.innerHTML = `<p style="padding:20px; color:var(--red);">Error loading reports: ${error.message}</p>`;
  }
}

async function openAdminReportModal(reportId) {
  try {
    const report = await request(`/api/admin/reports/${encodeURIComponent(reportId)}`);
    activeReviewReport = report;

    $("#adm-rep-id").textContent = report.report_id;
    const badge = $("#adm-rep-status-badge");
    const st = String(report.status || "PENDING").toLowerCase();
    badge.className = `status-pill ${st}`;
    badge.textContent = report.status;

    const delBadge = $("#adm-rep-deleted-badge");
    if (delBadge) {
      if (report.admin_deleted || report.user_deleted) {
        delBadge.classList.remove("hidden");
        delBadge.textContent = report.admin_deleted ? "ADMIN DELETED" : "USER DELETED";
      } else {
        delBadge.classList.add("hidden");
      }
    }

    $("#adm-rep-date").textContent = `Submitted: ${new Date(report.submitted_at).toLocaleString()}`;
    $("#adm-rep-user-name").textContent = report.user_full_name || "Unknown User";
    $("#adm-rep-user-id").textContent = report.user_id;
    $("#adm-rep-user-email").textContent = report.user_email || "";

    $("#adm-rep-category").textContent = report.category;
    $("#adm-rep-mode").textContent = report.transport_mode || "General";
    $("#adm-rep-route").textContent = report.related_route_info || "None specified";
    $("#adm-rep-title").textContent = report.title;
    $("#adm-rep-description").textContent = report.description;

    const evBox = $("#adm-rep-evidence-box");
    const evLink = $("#adm-rep-evidence-link");
    if (report.evidence_path) {
      evLink.href = report.evidence_path;
      evBox.classList.remove("hidden");
    } else {
      evBox.classList.add("hidden");
    }

    const pastRevBox = $("#adm-rep-past-review");
    const pastResp = $("#adm-rep-past-response");
    const pastMeta = $("#adm-rep-past-meta");
    if (report.reviewed_at) {
      pastRevBox.classList.remove("hidden");
      pastResp.textContent = report.admin_response || "(No written response text)";
      pastMeta.textContent = `Reviewed by ${report.reviewed_by || 'Admin'} at ${new Date(report.reviewed_at).toLocaleString()}`;
    } else {
      pastRevBox.classList.add("hidden");
    }

    // Set decision textarea
    $("#adm-decision-note").value = report.admin_response || "";

    // Quick moderation buttons
    $("#adm-rep-quick-warn-btn").onclick = () => {
      openWarnModal(report.user_id, report.user_full_name);
    };
    $("#adm-rep-quick-block-btn").onclick = () => {
      openBlockModal(report.user_id, report.user_full_name);
    };

    // Soft delete button
    $("#adm-rep-soft-delete-btn").onclick = () => {
      deleteAdminReport(report.report_id);
    };

    // Verify button
    $("#adm-rep-verify-btn").onclick = async () => {
      const note = $("#adm-decision-note").value.trim();
      try {
        await request(`/api/admin/reports/${encodeURIComponent(report.report_id)}/verify`, {
          method: "POST",
          body: JSON.stringify({ admin_response: note || null }),
        });
        show(`Report ${report.report_id} verified. User has been notified.`, "success");
        closeModal("admin-report-modal");
        loadAdminReports();
      } catch (err) {
        alert(`Verification failed: ${err.message}`);
      }
    };

    // Reject button
    $("#adm-rep-reject-btn").onclick = async () => {
      const reason = $("#adm-decision-note").value.trim();
      if (!reason) {
        alert("A rejection reason is required so the reporting user understands why their report was rejected.");
        $("#adm-decision-note").focus();
        return;
      }
      try {
        await request(`/api/admin/reports/${encodeURIComponent(report.report_id)}/reject`, {
          method: "POST",
          body: JSON.stringify({ admin_response: reason }),
        });
        show(`Report ${report.report_id} rejected with reason. User has been notified.`, "info");
        closeModal("admin-report-modal");
        loadAdminReports();
      } catch (err) {
        alert(`Rejection failed: ${err.message}`);
      }
    };

    openModal("admin-report-modal");
  } catch (err) {
    alert(`Could not load report details: ${err.message}`);
  }
}

async function deleteAdminReport(reportId) {
  if (!confirm(`Soft delete report ${reportId} from the visible admin view? The database and audit logs will remain intact.`)) {
    return;
  }
  try {
    await request(`/api/admin/reports/${encodeURIComponent(reportId)}`, { method: "DELETE" });
    show(`Report ${reportId} soft deleted from admin view.`, "info");
    closeModal("admin-report-modal");
    loadAdminReports();
  } catch (err) {
    alert(`Failed to delete report: ${err.message}`);
  }
}

// Attach filter listeners for reports
$("#admin-report-filter-status")?.addEventListener("change", loadAdminReports);
$("#admin-report-filter-cat")?.addEventListener("change", loadAdminReports);
$("#admin-report-include-deleted")?.addEventListener("change", loadAdminReports);
$("#admin-report-search")?.addEventListener("input", () => {
  clearTimeout(window._repSearchTimeout);
  window._repSearchTimeout = setTimeout(loadAdminReports, 300);
});
$("#admin-report-reload-btn")?.addEventListener("click", loadAdminReports);

// -------------------------------------------------------------
// 3. User Accounts & Moderation
// -------------------------------------------------------------

let currentAdminUsers = [];
let targetModerationUserId = null;

async function loadAdminUsers() {
  const container = $("#admin-users-table");
  if (!container) return;
  container.innerHTML = "<p style='padding:20px;'>Loading user accounts...</p>";

  const statusVal = $("#admin-user-filter-status")?.value || "all";
  const searchVal = $("#admin-user-search")?.value.trim() || "";

  const params = new URLSearchParams();
  if (statusVal && statusVal !== "all") params.append("status_filter", statusVal);
  if (searchVal) params.append("search", searchVal);

  try {
    const users = await request(`/api/admin/users?${params.toString()}`);
    currentAdminUsers = users;

    if (!users.length) {
      container.innerHTML = "<p style='padding:20px; color:var(--text-muted);'>No users found matching your criteria.</p>";
      return;
    }

    const rows = users.map((u) => {
      const isBlocked = u.is_blocked;
      const statusPill = isBlocked
        ? `<span class="status-pill blocked" title="${escapeHtml(u.blocked_reason || 'Blocked')}">Blocked</span>`
        : `<span class="status-pill active">Active</span>`;
      const warnPill = u.warnings_count > 0
        ? `<span class="status-pill warned">${u.warnings_count} Warning${u.warnings_count > 1 ? 's' : ''}</span>`
        : `<span style="color:var(--text-muted); font-size:0.8rem;">0</span>`;

      return `
        <tr>
          <td><strong style="font-family:monospace; color:var(--teal);">${escapeHtml(u.user_id)}</strong></td>
          <td><strong>${escapeHtml(u.full_name)}</strong></td>
          <td>${escapeHtml(u.email)}</td>
          <td>${statusPill}</td>
          <td>${warnPill}</td>
          <td>${u.reports_count}</td>
          <td>${new Date(u.created_at).toLocaleDateString()}</td>
          <td style="white-space:nowrap;">
            <button class="button secondary small" style="height:28px; padding:0 8px; font-size:0.75rem;" data-warn-user="${escapeHtml(u.user_id)}" data-user-name="${escapeHtml(u.full_name)}">
              ⚠️ Warn
            </button>
            <button class="button outline small" style="height:28px; padding:0 8px; font-size:0.75rem; margin-left:3px;" data-view-warns="${escapeHtml(u.user_id)}">
              📜 Warnings
            </button>
            ${isBlocked ? `
              <button class="button primary small" style="height:28px; padding:0 8px; font-size:0.75rem; background:#16a34a; border-color:#16a34a; margin-left:3px;" data-unblock-user="${escapeHtml(u.user_id)}">
                🔓 Unblock
              </button>
            ` : `
              <button class="button danger small" style="height:28px; padding:0 8px; font-size:0.75rem; margin-left:3px;" data-block-user="${escapeHtml(u.user_id)}" data-user-name="${escapeHtml(u.full_name)}">
                ⛔ Block
              </button>
            `}
            <button class="button outline small" style="height:28px; padding:0 8px; font-size:0.75rem; margin-left:3px;" data-block-hist="${escapeHtml(u.user_id)}">
              🔒 History
            </button>
          </td>
        </tr>
      `;
    }).join("");

    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>User ID</th>
            <th>Full Name</th>
            <th>Email</th>
            <th>Status</th>
            <th>Warnings</th>
            <th>Reports</th>
            <th>Joined</th>
            <th>Moderation Actions</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;

    container.querySelectorAll("[data-warn-user]").forEach((btn) => {
      btn.addEventListener("click", () => openWarnModal(btn.dataset.warnUser, btn.dataset.userName));
    });

    container.querySelectorAll("[data-view-warns]").forEach((btn) => {
      btn.addEventListener("click", () => openViewWarningsModal(btn.dataset.viewWarns));
    });

    container.querySelectorAll("[data-block-user]").forEach((btn) => {
      btn.addEventListener("click", () => openBlockModal(btn.dataset.blockUser, btn.dataset.userName));
    });

    container.querySelectorAll("[data-unblock-user]").forEach((btn) => {
      btn.addEventListener("click", () => unblockUser(btn.dataset.unblockUser));
    });

    container.querySelectorAll("[data-block-hist]").forEach((btn) => {
      btn.addEventListener("click", () => openBlockHistoryModal(btn.dataset.blockHist));
    });
  } catch (error) {
    container.innerHTML = `<p style="padding:20px; color:var(--red);">Error loading users: ${error.message}</p>`;
  }
}

// User Warning Modal
function openWarnModal(userId, userName = "") {
  targetModerationUserId = userId;
  $("#adm-warn-user-label").textContent = `User: ${userName || userId} (${userId})`;
  $("#adm-warn-reason").value = "";
  openModal("admin-warn-modal");
}

$("#admin-warn-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!targetModerationUserId) return;
  const reason = $("#adm-warn-reason").value.trim();
  if (!reason) {
    alert("Warning reason is required.");
    return;
  }
  try {
    await request(`/api/admin/users/${encodeURIComponent(targetModerationUserId)}/warn`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
    show(`Official warning dispatched to user ${targetModerationUserId}.`, "success");
    closeModal("admin-warn-modal");
    loadAdminUsers();
  } catch (err) {
    alert(`Could not issue warning: ${err.message}`);
  }
});

// View Warnings Modal
async function openViewWarningsModal(userId) {
  $("#adm-vw-user-label").textContent = `User: ${userId}`;
  const container = $("#adm-warnings-table");
  container.innerHTML = "<p style='padding:14px;'>Loading user warnings...</p>";
  openModal("admin-view-warnings-modal");

  try {
    const warnings = await request(`/api/admin/users/${encodeURIComponent(userId)}/warnings`);
    if (!warnings.length) {
      container.innerHTML = "<p style='padding:14px; color:var(--text-muted);'>No warnings recorded for this user.</p>";
      return;
    }
    const rows = warnings.map((w) => `
      <tr>
        <td>#${w.id}</td>
        <td><strong>${escapeHtml(w.reason)}</strong></td>
        <td>${escapeHtml(w.admin_id)}</td>
        <td>${new Date(w.created_at).toLocaleString()}</td>
      </tr>
    `).join("");
    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Warning ID</th>
            <th>Reason</th>
            <th>Issued By</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (err) {
    container.innerHTML = `<p style='padding:14px; color:var(--red);'>Failed to load warnings: ${err.message}</p>`;
  }
}

// Block User Modal
function openBlockModal(userId, userName = "") {
  targetModerationUserId = userId;
  $("#adm-block-user-label").textContent = `User: ${userName || userId} (${userId})`;
  $("#adm-block-reason").value = "";
  openModal("admin-block-modal");
}

$("#admin-block-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!targetModerationUserId) return;
  const reason = $("#adm-block-reason").value.trim();
  if (!reason) {
    alert("Suspension reason is required.");
    return;
  }
  try {
    await request(`/api/admin/users/${encodeURIComponent(targetModerationUserId)}/block`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
    show(`User ${targetModerationUserId} has been suspended/blocked.`, "info");
    closeModal("admin-block-modal");
    loadAdminUsers();
  } catch (err) {
    alert(`Could not block user: ${err.message}`);
  }
});

// Unblock user
async function unblockUser(userId) {
  const reason = prompt(`Provide an optional unblock reason/note for user ${userId}:`, "Administrative review; account restored.");
  if (reason === null) return;
  try {
    await request(`/api/admin/users/${encodeURIComponent(userId)}/unblock`, {
      method: "POST",
      body: JSON.stringify({ reason: reason.trim() || "Unblocked by administrator." }),
    });
    show(`User ${userId} unblocked successfully.`, "success");
    loadAdminUsers();
  } catch (err) {
    alert(`Could not unblock user: ${err.message}`);
  }
}

// View Block History Modal
async function openBlockHistoryModal(userId) {
  $("#adm-bh-user-label").textContent = `User: ${userId}`;
  const container = $("#adm-block-history-table");
  container.innerHTML = "<p style='padding:14px;'>Loading account block/unblock history...</p>";
  openModal("admin-block-history-modal");

  try {
    const history = await request(`/api/admin/users/${encodeURIComponent(userId)}/block-history`);
    if (!history.length) {
      container.innerHTML = "<p style='padding:14px; color:var(--text-muted);'>No block/unblock events recorded for this user.</p>";
      return;
    }
    const rows = history.map((h) => {
      const isBlk = h.action === "BLOCK";
      const actBadge = isBlk
        ? '<span class="status-pill blocked">BLOCK</span>'
        : '<span class="status-pill active">UNBLOCK</span>';
      return `
        <tr>
          <td>${actBadge}</td>
          <td><strong>${escapeHtml(h.reason || '')}</strong></td>
          <td>${escapeHtml(h.admin_id)}</td>
          <td>${new Date(h.created_at).toLocaleString()}</td>
        </tr>
      `;
    }).join("");
    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Reason</th>
            <th>Admin</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (err) {
    container.innerHTML = `<p style='padding:14px; color:var(--red);'>Failed to load history: ${err.message}</p>`;
  }
}

// User filter listeners
$("#admin-user-filter-status")?.addEventListener("change", loadAdminUsers);
$("#admin-user-search")?.addEventListener("input", () => {
  clearTimeout(window._userSearchTimeout);
  window._userSearchTimeout = setTimeout(loadAdminUsers, 300);
});
$("#admin-user-reload-btn")?.addEventListener("click", loadAdminUsers);

// -------------------------------------------------------------
// 4. Audit Logs
// -------------------------------------------------------------

async function loadAuditLogs() {
  const container = $("#admin-audit-list");
  container.innerHTML = "<p style='padding:20px;'>Loading administrative audit history...</p>";
  try {
    const logs = await request("/api/admin/audit-logs");
    if (!logs.length) {
      container.innerHTML = "<p style='padding:20px; color:var(--text-muted);'>No audit logs recorded yet.</p>";
      return;
    }

    const rows = logs.map((l) => `
      <tr>
        <td><strong>${escapeHtml(l.actor)}</strong></td>
        <td><span class="pill train" style="font-size:0.75rem;">${escapeHtml(l.action)}</span></td>
        <td>${escapeHtml(l.target_type)} ${l.target_id ? `(${escapeHtml(l.target_id)})` : ''}</td>
        <td style="font-family:monospace; font-size:0.8rem; max-width:320px; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(JSON.stringify(l.details || {}))}</td>
        <td>${new Date(l.created_at).toLocaleString()}</td>
      </tr>
    `).join("");

    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Actor</th>
            <th>Action</th>
            <th>Target Entity</th>
            <th>Details</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (error) {
    container.innerHTML = `<p style="padding:20px; color:var(--red);">Error loading audit logs: ${error.message}</p>`;
  }
}

if ($("#reload-audit-btn")) {
  $("#reload-audit-btn").addEventListener("click", loadAuditLogs);
}

// -------------------------------------------------------------
// 5. Operational Transport Records CRUD (Preserved)
// -------------------------------------------------------------

function selected() { return definitions[$("#entity").value]; }

function renderForm(row = {}) {
  const definition = selected();
  if (!definition) return;
  editingKey = row[definition.key] ?? null;
  const fields = definition.fields.map(([name, label, type]) => {
    const rawValue = row[name] ?? "";
    const value = name === "value" && typeof rawValue !== "string" ? JSON.stringify(rawValue) : rawValue;
    return `
      <label>${label}
        <input name="${name}" type="${type}" value="${escapeHtml(value)}" ${name.endsWith("_km") || name.includes("distance") || name === "stop_order" ? 'step="any"' : ""} required>
      </label>
    `;
  }).join("");

  $("#record-form").innerHTML = `
    ${fields}
    <div style="display: flex; gap: 8px;">
      <button class="button primary" type="submit">${editingKey === null ? "Add Record" : "Save Changes"}</button>
      <button id="cancel-edit" class="button secondary" type="button">Reset</button>
    </div>
  `;
  $("#cancel-edit").addEventListener("click", () => renderForm());
}

function renderRows(rows) {
  currentRows = rows;
  const definition = selected();
  if (!rows.length) {
    $("#record-list").innerHTML = "<p style='padding: 20px; color: var(--text-muted);'>No records found in this table.</p>";
    return;
  }
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  const headings = columns.map((key) => `<th>${key.replaceAll("_", " ").toUpperCase()}</th>`).join("");
  const body = rows.map((row) => `
    <tr>
      ${columns.map((key) => `<td>${escapeHtml(typeof row[key] === "object" ? JSON.stringify(row[key]) : row[key])}</td>`).join("")}
      <td style="white-space:nowrap;">
        ${definition.immutable ? "" : `<button class="button secondary" style="height:28px;padding:0 8px;margin-right:4px;font-size:0.8rem;" data-edit="${escapeHtml(row[definition.key])}">Edit</button>`}
        ${definition.config ? "" : `<button class="button danger" style="height:28px;padding:0 8px;font-size:0.8rem;" data-delete="${escapeHtml(row[definition.key])}">Delete</button>`}
      </td>
    </tr>
  `).join("");

  $("#record-list").innerHTML = `
    <table>
      <thead>
        <tr>${headings}<th>ACTIONS</th></tr>
      </thead>
      <tbody>${body}</tbody>
    </table>
  `;

  document.querySelectorAll("[data-edit]").forEach((button) => {
    button.addEventListener("click", () => {
      const row = currentRows.find((item) => String(item[definition.key]) === button.dataset.edit);
      if (row) renderForm(row);
    });
  });

  document.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      const deleteKey = button.dataset.delete || button.getAttribute("data-delete");
      if (!deleteKey) {
        show("Cannot delete: record key is missing.", "error");
        return;
      }
      if (!confirm(`Permanently delete ${definition.key} = ${deleteKey}?`)) return;
      try {
        await request(`${definition.endpoint}/${encodeURIComponent(deleteKey)}`, { method: "DELETE" });
        show("Record deleted successfully.", "info");
        await loadEntity();
      } catch (error) {
        show(error.message, "error");
      }
    });
  });
}

async function loadEntity() {
  const definition = selected();
  if (!definition) return;
  renderForm();
  show("Loading records...", "info");
  try {
    const rows = await request(definition.endpoint);
    renderRows(rows);
    show();
  } catch (error) {
    show(error.message, "error");
  }
}

// -------------------------------------------------------------
// Admin Login & Setup
// -------------------------------------------------------------

function setupWorkspace() {
  const entitySelect = $("#entity");
  if (!entitySelect) return;
  entitySelect.replaceChildren();
  for (const [key, value] of Object.entries(definitions)) {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = value.label || key.replaceAll("-", " ").toUpperCase();
    entitySelect.append(option);
  }
  entitySelect.removeEventListener("change", loadEntity);
  entitySelect.addEventListener("change", loadEntity);
  const reloadBtn = $("#reload");
  if (reloadBtn) {
    reloadBtn.removeEventListener("click", loadEntity);
    reloadBtn.addEventListener("click", loadEntity);
  }
}

function enterWorkspace(adminName = "Administrator") {
  $("#login-section").classList.add("hidden");
  $("#admin-workspace").classList.remove("hidden");
  const logoutBtn = $("#admin-logout-btn");
  if (logoutBtn) logoutBtn.classList.remove("hidden");
  const adminUserInfo = $("#admin-user-info");
  if (adminUserInfo) adminUserInfo.classList.remove("hidden");
  const adminDisplayName = $("#admin-display-name");
  if (adminDisplayName) adminDisplayName.textContent = adminName;
  show(`Logged in as ${escapeHtml(adminName)}. PostgreSQL transport records ready for management.`, "success");
  setupWorkspace();
  loadAdminOverview();
}

async function autoLoginAdmin() {
  const token = localStorage.getItem("token");
  if (!token) return;

  try {
    const meRes = await fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!meRes.ok) return;
    const user = await meRes.json();
    if (user && user.role === "admin") {
      authorization = `Bearer ${token}`;
      enterWorkspace(user.full_name || "Administrator");
    }
  } catch {
    // If verification fails, keep login prompt
  }
}

// Log out button listener
const logoutBtn = $("#admin-logout-btn");
if (logoutBtn) {
  logoutBtn.addEventListener("click", () => {
    localStorage.removeItem("token");
    authorization = "";
    $("#admin-workspace").classList.add("hidden");
    $("#login-section").classList.remove("hidden");
    logoutBtn.classList.add("hidden");
    const adminUserInfo = $("#admin-user-info");
    if (adminUserInfo) adminUserInfo.classList.add("hidden");
    show("Logged out successfully.", "info");
  });
}

// Run auto-login check immediately on page load
autoLoginAdmin();

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = $("#username").value.trim();
  const password = $("#password").value;
  authorization = `Basic ${btoa(`${username}:${password}`)}`;
  show("Authenticating with administrative credentials...", "info");
  try {
    // Check administrative access
    await request("/api/admin/bus-schedules");

    // Seamlessly authorize user features and persist JWT token
    try {
      const uRes = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: username, password }),
      });
      if (uRes.ok) {
        const uData = await uRes.json();
        if (uData && uData.access_token) {
          localStorage.setItem("token", uData.access_token);
          authorization = `Bearer ${uData.access_token}`;
        }
      }
    } catch {
      // Non-blocking
    }

    enterWorkspace(username);
  } catch (error) {
    show(`Authentication failed: ${error.message}`, "error");
  }
});

$("#record-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const definition = selected();
  const form = new FormData(event.target);
  const payload = {};
  for (const [key, value] of form.entries()) {
    if (value === "") continue;
    if (key.endsWith("_km") || key.includes("distance") || key === "stop_order" || key === "day_offset") {
      payload[key] = Number(value);
    } else if (key === "value" && definition.config) {
      try {
        payload[key] = JSON.parse(value);
      } catch (error) {
        show("JSON parsing error: Value must be valid JSON", "error");
        return;
      }
    } else {
      payload[key] = value;
    }
  }

  try {
    if (editingKey === null) {
      await request(definition.endpoint, { method: "POST", body: JSON.stringify(payload) });
      show("Record added successfully.", "success");
    } else {
      await request(`${definition.endpoint}/${encodeURIComponent(editingKey)}`, { method: "PUT", body: JSON.stringify(payload) });
      show("Record updated successfully.", "success");
    }
    await loadEntity();
  } catch (error) {
    show(error.message, "error");
  }
});

// -------------------------------------------------------------
// 5. Admin Transport Disruption Management System
// -------------------------------------------------------------

let currentAdminDisruptions = [];
let activeAdminDisruption = null;
let disruptionCandidates = null;
let selectedDisruptionSegments = [];

async function loadAdminDisruptions() {
  const table = $("#admin-disruptions-table");
  if (!table) return;

  const statusFilter = $("#admin-disruption-filter-status")?.value || "all";
  const modeFilter = $("#admin-disruption-filter-mode")?.value || "all";
  const searchVal = $("#admin-disruption-search")?.value?.trim() || "";
  const includeDeleted = $("#admin-disruption-include-deleted")?.checked || false;

  table.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Loading transport disruption alerts...</div>';

  try {
    const params = new URLSearchParams();
    if (statusFilter !== "all") params.append("status", statusFilter);
    if (modeFilter !== "all") params.append("transport_mode", modeFilter);
    if (searchVal) params.append("search", searchVal);
    if (includeDeleted) params.append("include_deleted", "true");

    const queryStr = params.toString() ? `?${params.toString()}` : "";
    const list = await request(`/api/admin/disruptions${queryStr}`);
    currentAdminDisruptions = list;

    const activeCount = list.filter((d) => (d.status || "").toUpperCase() === "ACTIVE" && !d.deleted_at).length;
    const disBadge = $("#sidebar-disruptions-badge");
    if (disBadge) {
      disBadge.textContent = activeCount;
      disBadge.classList.toggle("hidden", activeCount === 0);
    }

    if (!list || list.length === 0) {
      table.innerHTML = `
        <div style="padding: 30px; text-align: center; color: var(--text-muted);">
          <span style="font-size: 2rem; display: block; margin-bottom: 8px;">🟢</span>
          <strong>No Transport Disruptions Found</strong>
          <p style="font-size: 0.85rem; margin-top: 4px;">No active or matching transport disruption alerts found. The transport network is running normally.</p>
        </div>
      `;
      return;
    }

    const rows = list.map((d) => {
      const statusPillClass = d.status.toLowerCase();
      const severityPillClass = d.severity.toLowerCase();
      const isArchived = Boolean(d.deleted_at);
      const segSummary = (d.affected_segments && d.affected_segments.length > 0)
        ? d.affected_segments.map((s) => escapeHtml(s.segment_description || s.affected_segment_id)).join(", ")
        : `<span style="color: var(--text-muted);">${escapeHtml(d.location_name)} (Area)</span>`;

      const estEnd = d.estimated_end_time
        ? escapeHtml(d.estimated_end_time.replace("T", " ").slice(0, 16))
        : '<span style="color: var(--text-muted);">&mdash;</span>';

      return `
        <tr>
          <td><strong style="font-family: monospace; color: var(--navy);">${escapeHtml(d.disruption_id)}</strong></td>
          <td>
            <span class="status-pill ${statusPillClass}">${escapeHtml(d.status)}</span>
            ${isArchived ? '<span class="status-pill rejected" style="font-size: 0.65rem; margin-left: 4px;">ARCHIVED</span>' : ''}
          </td>
          <td><span class="pill ${escapeHtml(d.transport_mode)}">${escapeHtml(d.transport_mode)}</span></td>
          <td><span class="status-pill ${severityPillClass}">${escapeHtml(d.severity)}</span></td>
          <td>
            <strong>${escapeHtml(d.title)}</strong>
            <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">📍 ${escapeHtml(d.location_name)}</div>
          </td>
          <td><span style="font-size: 0.82rem; font-weight: 600;">${escapeHtml(d.cause)}</span></td>
          <td style="max-width: 180px; font-size: 0.8rem;">${segSummary}</td>
          <td style="font-size: 0.8rem;">${estEnd}</td>
          <td>
            <div style="display: flex; gap: 6px; align-items: center;">
              <button type="button" class="button secondary small" onclick="openDisruptionDetailModal('${escapeHtml(d.disruption_id)}')" style="font-size: 0.75rem; height: 28px; padding: 0 8px;">
                Manage ➔
              </button>
              ${d.status === "DRAFT" || d.status === "INACTIVE" ? `
                <button type="button" class="button small" onclick="quickSetDisruptionStatus('${escapeHtml(d.disruption_id)}', 'ACTIVE')" style="background: #16a34a; border-color: #16a34a; color: white; font-size: 0.75rem; height: 28px; padding: 0 8px;">
                  ⚡ Activate
                </button>
              ` : ''}
              ${d.status === "ACTIVE" ? `
                <button type="button" class="button outline small" onclick="quickSetDisruptionStatus('${escapeHtml(d.disruption_id)}', 'INACTIVE')" style="font-size: 0.75rem; height: 28px; padding: 0 8px;">
                  ⏸️ Deactivate
                </button>
              ` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join("");

    table.innerHTML = `
      <div style="overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>Alert ID</th>
              <th>Status</th>
              <th>Mode</th>
              <th>Severity</th>
              <th>Incident Title / Location</th>
              <th>Cause</th>
              <th>Affected Segments</th>
              <th>Est. Clearance</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  } catch (error) {
    table.innerHTML = `<div style="padding: 20px; color: #dc2626;">Failed to load disruptions: ${escapeHtml(error.message)}</div>`;
  }
}

async function loadDisruptionCandidates() {
  if (disruptionCandidates) return disruptionCandidates;
  try {
    disruptionCandidates = await request("/api/admin/disruptions/segments/candidates");
    return disruptionCandidates;
  } catch {
    return { road_segments: [], rail_stations: [] };
  }
}

let lastAnalyzedDisruption = null;

function openCreateDisruptionModal() {
  const modal = $("#admin-create-disruption-modal");
  if (!modal) return;

  $("#adm-dis-edit-id").value = "";
  $("#adm-dis-desc").value = "";
  $("#adm-dis-source-name").value = "";
  $("#adm-dis-source-url").value = "";
  const locInput = $("#adm-dis-corrected-loc");
  if (locInput) locInput.value = "";

  $("#adm-dis-preview-container").classList.add("hidden");
  $("#adm-dis-clarify-box").classList.add("hidden");
  lastAnalyzedDisruption = null;

  modal.classList.remove("hidden");
}

async function analyzeDisruptionDescription(forceCorrectedLoc = null) {
  const desc = $("#adm-dis-desc")?.value?.trim();
  if (!desc) {
    show("Please enter an incident description to analyze.", "error");
    return null;
  }

  const sourceName = $("#adm-dis-source-name")?.value?.trim() || null;
  const sourceUrl = $("#adm-dis-source-url")?.value?.trim() || null;
  const correctedLoc = forceCorrectedLoc !== null 
    ? forceCorrectedLoc 
    : ($("#adm-dis-corrected-loc")?.value?.trim() || null);

  const btn = $("#adm-dis-analyze-btn");
  if (btn) btn.textContent = "Analyzing Network Routes...";

  try {
    const payload = {
      description: desc,
      source_name: sourceName,
      source_url: sourceUrl,
    };
    if (correctedLoc) {
      payload.corrected_location = correctedLoc;
    }

    const data = await request("/api/admin/disruptions/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    lastAnalyzedDisruption = data;

    const previewContainer = $("#adm-dis-preview-container");
    const clarifyBox = $("#adm-dis-clarify-box");
    const clarifyMsg = $("#adm-dis-clarify-msg");

    previewContainer.classList.remove("hidden");

    if (data.status === "NEEDS_CLARIFICATION") {
      clarifyBox.classList.remove("hidden");
      clarifyMsg.textContent = data.clarification_message || "Please provide more details on the affected location or transport mode.";
      $("#adm-dis-prev-loc").textContent = data.extracted.location || "Unclear";
      $("#adm-dis-prev-mode").textContent = data.extracted.transport_mode || "Unclear";
      $("#adm-dis-prev-type").textContent = data.extracted.incident_type || "Unclear";
      $("#adm-dis-prev-impact").textContent = data.extracted.operational_impact || "Unclear";
      
      const confBadge = $("#adm-dis-prev-confidence");
      if (confBadge) {
        confBadge.className = "status-pill pending";
        confBadge.textContent = data.extracted.matching_status || "NEEDS CLARIFICATION";
      }

      $("#adm-dis-prev-alert-msg").textContent = data.extracted.alert_message || "Alert cannot be generated until details are clarified.";
      $("#adm-dis-route-count-badge").textContent = "0 Routes (Clarification required)";
      $("#adm-dis-route-count-badge").className = "status-pill pending";
      $("#adm-dis-detected-routes-list").innerHTML = '<p style="font-size: 0.8rem; color: #92400e; margin: 4px 0;">Routes cannot be accurately identified until incident details are clarified.</p>';
      
      const locIn = $("#adm-dis-corrected-loc");
      if (locIn && !locIn.value && data.extracted.location) {
        locIn.value = data.extracted.location;
      }
      return data;
    }

    clarifyBox.classList.add("hidden");
    const ext = data.extracted;
    $("#adm-dis-prev-loc").textContent = ext.location || "-";
    
    const locIn = $("#adm-dis-corrected-loc");
    if (locIn && (!locIn.value || forceCorrectedLoc === null)) {
      locIn.value = ext.location || "";
    }

    $("#adm-dis-prev-mode").textContent = ext.transport_mode || "-";
    $("#adm-dis-prev-type").textContent = ext.incident_type || "-";
    $("#adm-dis-prev-impact").textContent = ext.operational_impact || "-";

    const sevBadge = $("#adm-dis-preview-sev-badge");
    if (sevBadge) {
      sevBadge.className = `status-pill ${(ext.severity || "moderate").toLowerCase()}`;
      sevBadge.textContent = ext.severity;
    }

    const confBadge = $("#adm-dis-prev-confidence");
    if (confBadge) {
      confBadge.className = "status-pill active";
      confBadge.textContent = `${ext.matching_status || "CONFIDENT MATCH"} (${ext.matching_confidence || "HIGH"})`;
    }

    $("#adm-dis-prev-alert-msg").textContent = ext.alert_message;

    const countBadge = $("#adm-dis-route-count-badge");
    countBadge.textContent = `${data.total_affected_routes} Route${data.total_affected_routes === 1 ? "" : "s"} Detected`;
    countBadge.className = "status-pill active";

    const routesList = $("#adm-dis-detected-routes-list");
    if (!data.affected_routes || data.affected_routes.length === 0) {
      routesList.innerHTML = '<p style="font-size: 0.8rem; color: var(--text-muted); margin: 4px 0;">No active scheduled routes currently traverse this specific network section.</p>';
    } else {
      routesList.innerHTML = data.affected_routes.map(r => `
        <div style="display: flex; justify-content: space-between; align-items: center; background: white; border: 1px solid var(--border); border-radius: 6px; padding: 6px 10px; font-size: 0.8rem;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="pill ${escapeHtml(r.mode)}" style="font-size: 0.68rem; padding: 1px 6px;">${escapeHtml(r.mode)}</span>
            <strong>${escapeHtml(r.service)}</strong>
            <span style="color: var(--text-muted); font-size: 0.78rem;">(${escapeHtml(r.origin)} ➔ ${escapeHtml(r.destination)})</span>
          </div>
          <span style="font-size: 0.75rem; color: #ea580c; font-weight: 600;">📍 ${escapeHtml(r.matched_section)}</span>
        </div>
      `).join("");
    }

    return data;
  } catch (err) {
    show(`Analysis failed: ${err.message}`, "error");
    return null;
  } finally {
    if (btn) btn.textContent = "🔍 Analyze Incident & Detect Routes";
  }
}

$("#adm-dis-analyze-btn")?.addEventListener("click", () => analyzeDisruptionDescription());

$("#adm-dis-reanalyze-loc-btn")?.addEventListener("click", () => {
  const corrected = $("#adm-dis-corrected-loc")?.value?.trim();
  analyzeDisruptionDescription(corrected || null);
});

document.addEventListener("click", (e) => {
  const exampleBtn = e.target.closest(".adm-dis-example-pill");
  if (exampleBtn) {
    const text = exampleBtn.getAttribute("data-example");
    if (text) {
      const descEl = $("#adm-dis-desc");
      if (descEl) descEl.value = text;
      const locIn = $("#adm-dis-corrected-loc");
      if (locIn) locIn.value = "";
      analyzeDisruptionDescription(null);
    }
  }
});

$("#admin-create-disruption-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const desc = $("#adm-dis-desc")?.value?.trim();
  if (!desc) {
    show("Please enter an incident description.", "error");
    return;
  }

  const sourceName = $("#adm-dis-source-name")?.value?.trim() || null;
  const sourceUrl = $("#adm-dis-source-url")?.value?.trim() || null;
  const correctedLoc = $("#adm-dis-corrected-loc")?.value?.trim() || null;

  // Run or ensure analysis was performed
  let analysis = lastAnalyzedDisruption;
  if (!analysis) {
    analysis = await analyzeDisruptionDescription(correctedLoc);
  }

  if (!analysis || analysis.status === "NEEDS_CLARIFICATION") {
    show("Cannot publish alert: " + (analysis?.clarification_message || "Please clarify incident details first."), "error");
    return;
  }

  const submitBtn = $("#adm-dis-submit-btn");
  if (submitBtn) submitBtn.disabled = true;

  try {
    const res = await request("/api/admin/disruptions/publish-simplified", {
      method: "POST",
      body: JSON.stringify({
        description: desc,
        source_name: sourceName,
        source_url: sourceUrl,
        corrected_location: correctedLoc,
      }),
    });

    show(`Disruption alert ${res.disruption_id} published successfully! Dynamic route alerts are now active.`, "success");
    $("#admin-create-disruption-modal").classList.add("hidden");
    await loadAdminDisruptions();
  } catch (err) {
    show(`Publishing failed: ${err.message}`, "error");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
});

async function openDisruptionDetailModal(disruptionId) {
  const modal = $("#admin-disruption-detail-modal");
  if (!modal) return;

  try {
    const d = await request(`/api/admin/disruptions/${encodeURIComponent(disruptionId)}`);
    activeAdminDisruption = d;

    $("#adm-dd-title").textContent = d.title;
    $("#adm-dd-id").textContent = `${d.disruption_id} • Location: ${d.location_name}`;

    const stBadge = $("#adm-dd-status-badge");
    stBadge.className = `status-pill ${d.status.toLowerCase()}`;
    stBadge.textContent = d.status;

    const modeBadge = $("#adm-dd-mode-badge");
    modeBadge.className = `pill ${d.transport_mode}`;
    modeBadge.textContent = d.transport_mode;

    const sevBadge = $("#adm-dd-severity-badge");
    sevBadge.className = `status-pill ${d.severity.toLowerCase()}`;
    sevBadge.textContent = d.severity;

    $("#adm-dd-dates").textContent = `Created: ${d.created_at.replace("T", " ").slice(0, 16)}`;
    $("#adm-dd-alert-msg").textContent = d.alert_message;
    $("#adm-dd-desc").textContent = d.description;

    const segBox = $("#adm-dd-segments");
    if (d.affected_segments && d.affected_segments.length > 0) {
      segBox.innerHTML = d.affected_segments.map(s => `
        <div style="margin: 4px 0;">
          <span class="pill ${escapeHtml(s.transport_mode)}" style="font-size: 0.72rem; padding: 1px 6px;">${escapeHtml(s.transport_mode)}</span>
          <strong>${escapeHtml(s.segment_description)}</strong>
          <span style="font-family: monospace; color: var(--text-muted); font-size: 0.78rem;">(${escapeHtml(s.affected_segment_id)})</span>
        </div>
      `).join("");
    } else {
      segBox.innerHTML = `<em>District-wide disruption matching all ${escapeHtml(d.transport_mode)} routes traversing ${escapeHtml(d.location_name)}.</em>`;
    }

    const metaBox = $("#adm-dd-meta-box");
    let metaHtml = `
      <div><b>Cause:</b> ${escapeHtml(d.cause)}</div>
      <div><b>Created By Admin:</b> ${escapeHtml(d.created_by_admin_id)}</div>
      ${d.activated_at ? `<div><b>Activated At:</b> ${escapeHtml(d.activated_at.replace("T", " ").slice(0, 16))}</div>` : ''}
      ${d.resolved_at ? `<div><b>Resolved At:</b> ${escapeHtml(d.resolved_at.replace("T", " ").slice(0, 16))}</div>` : ''}
      ${d.estimated_end_time ? `<div><b>Estimated End:</b> ${escapeHtml(d.estimated_end_time.replace("T", " ").slice(0, 16))}</div>` : ''}
      ${d.source_name ? `<div><b>Source Name:</b> ${escapeHtml(d.source_name)} ${d.source_url ? `(<a href="${escapeHtml(d.source_url)}" target="_blank">Link</a>)` : ''}</div>` : ''}
      ${d.admin_notes ? `<div><b>Internal Notes:</b> ${escapeHtml(d.admin_notes)}</div>` : ''}
    `;
    metaBox.innerHTML = metaHtml;

    // Button states
    $("#adm-dd-activate-btn").style.display = d.status === "ACTIVE" ? "none" : "inline-block";
    $("#adm-dd-deactivate-btn").style.display = d.status === "ACTIVE" ? "inline-block" : "none";
    $("#adm-dd-resolve-btn").style.display = d.status === "RESOLVED" ? "none" : "inline-block";
    $("#adm-dd-cancel-btn").style.display = d.status === "CANCELLED" ? "none" : "inline-block";

    modal.classList.remove("hidden");
  } catch (err) {
    show(`Failed to fetch disruption details: ${err.message}`, "error");
  }
}

async function quickSetDisruptionStatus(disruptionId, newStatus) {
  try {
    const actionMap = {
      "ACTIVE": "activate",
      "INACTIVE": "deactivate",
      "RESOLVED": "resolve",
      "CANCELLED": "cancel",
    };
    const actionPath = actionMap[newStatus.toUpperCase()] || newStatus.toLowerCase();
    const endpoint = `/api/admin/disruptions/${encodeURIComponent(disruptionId)}/${actionPath}`;
    await request(endpoint, { method: "POST", body: JSON.stringify({}) });
    show(`Disruption ${disruptionId} status set to ${newStatus}.`, "success");
    await loadAdminDisruptions();
  } catch (err) {
    show(`Failed to update status: ${err.message}`, "error");
  }
}

async function setDisruptionStatusFromModal(newStatus) {
  if (!activeAdminDisruption) return;
  const id = activeAdminDisruption.disruption_id;
  await quickSetDisruptionStatus(id, newStatus);
  await openDisruptionDetailModal(id);
}

// Expose on window for inline event handlers in rendered tables
window.openDisruptionDetailModal = openDisruptionDetailModal;
window.quickSetDisruptionStatus = quickSetDisruptionStatus;
window.setDisruptionStatusFromModal = setDisruptionStatusFromModal;

$("#adm-dd-activate-btn")?.addEventListener("click", () => setDisruptionStatusFromModal("ACTIVE"));
$("#adm-dd-deactivate-btn")?.addEventListener("click", () => setDisruptionStatusFromModal("INACTIVE"));
$("#adm-dd-resolve-btn")?.addEventListener("click", () => setDisruptionStatusFromModal("RESOLVED"));
$("#adm-dd-cancel-btn")?.addEventListener("click", () => setDisruptionStatusFromModal("CANCELLED"));

$("#adm-dd-delete-btn")?.addEventListener("click", async () => {
  if (!activeAdminDisruption) return;
  const id = activeAdminDisruption.disruption_id;
  if (!confirm(`Are you sure you want to soft delete disruption ${id}? It will be archived and removed from route alerts.`)) return;

  try {
    await request(`/api/admin/disruptions/${encodeURIComponent(id)}`, { method: "DELETE" });
    show(`Disruption ${id} soft deleted / archived.`, "success");
    $("#admin-disruption-detail-modal").classList.add("hidden");
    await loadAdminDisruptions();
  } catch (err) {
    show(`Failed to delete disruption: ${err.message}`, "error");
  }
});

$("#adm-dd-audit-btn")?.addEventListener("click", () => {
  if (!activeAdminDisruption) return;
  openDisruptionAuditModal(activeAdminDisruption.disruption_id);
});

async function openDisruptionAuditModal(disruptionId) {
  const modal = $("#admin-disruption-audit-modal");
  const table = $("#adm-dis-audit-table");
  if (!modal || !table) return;

  $("#adm-dis-audit-id").textContent = `Disruption: ${disruptionId}`;
  table.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--text-muted);">Loading audit history...</div>';
  modal.classList.remove("hidden");

  try {
    const logs = await request(`/api/admin/disruptions/${encodeURIComponent(disruptionId)}/audit-logs`);
    if (!logs || logs.length === 0) {
      table.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">No audit events recorded for this disruption.</div>';
      return;
    }

    const rows = logs.map(l => `
      <tr>
        <td style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(l.created_at.replace("T", " ").slice(0, 16))}</td>
        <td><strong style="color: var(--teal); font-size: 0.8rem;">${escapeHtml(l.admin_id)}</strong></td>
        <td><span class="status-pill ${escapeHtml((l.action || '').toLowerCase())}" style="font-size: 0.72rem;">${escapeHtml(l.action)}</span></td>
        <td><span class="status-pill ${escapeHtml((l.new_status || '').toLowerCase())}" style="font-size: 0.72rem;">${escapeHtml(l.new_status)}</span></td>
        <td style="font-size: 0.82rem;">${escapeHtml(l.change_description)}</td>
      </tr>
    `).join("");

    table.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Admin ID</th>
            <th>Action</th>
            <th>Result Status</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (err) {
    table.innerHTML = `<div style="padding: 16px; color: #dc2626;">Failed to load audit history: ${escapeHtml(err.message)}</div>`;
  }
}

window.openDisruptionAuditModal = openDisruptionAuditModal;

// Disruption Filter & Creation Event Listeners
$("#admin-disruption-create-btn")?.addEventListener("click", () => openCreateDisruptionModal());
$("#admin-disruption-reload-btn")?.addEventListener("click", () => loadAdminDisruptions());
$("#admin-disruption-filter-status")?.addEventListener("change", () => loadAdminDisruptions());
$("#admin-disruption-filter-mode")?.addEventListener("change", () => loadAdminDisruptions());
$("#admin-disruption-include-deleted")?.addEventListener("change", () => loadAdminDisruptions());
$("#admin-disruption-search")?.addEventListener("input", () => loadAdminDisruptions());

