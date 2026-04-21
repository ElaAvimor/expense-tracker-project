console.log("SCRIPT LOADED");
const API_BASE =
  window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000"
    : "https://expense-backend-1065487092168.us-central1.run.app/";

// ── State ────────────────────────────────────────────────

let previewData = null;
let importsList = [];
// "latest" | "all" | number (specific import_id)
let currentScope = "latest";

// ── DOM refs ─────────────────────────────────────────────

const fileInput = document.getElementById("file-input");
const confirmBtn = document.getElementById("confirm-btn");
const statusEl = document.getElementById("status-message");

const previewSection = document.getElementById("preview-section");
const closePreviewBtn = document.getElementById("close-preview-btn");
const previewFilename = document.getElementById("preview-filename");
const previewSkipped = document.getElementById("preview-skipped");
const previewCount = document.getElementById("preview-count");
const previewTableBody = document.querySelector("#preview-table tbody");

const dashboardArea = document.getElementById("dashboard-area");
const importsListEl = document.getElementById("imports-list");
const scopeLatestBtn = document.getElementById("scope-latest-btn");
const scopeAllBtn = document.getElementById("scope-all-btn");

const dashboardSection = document.getElementById("dashboard-section");
const dashTotalTx = document.getElementById("dash-total-transactions");
const dashTotalAmt = document.getElementById("dash-total-amount");
const dashTopCategory = document.getElementById("dash-top-category");
const dashTopCategoryMeta = document.getElementById("dash-top-category-meta");
const dashScopeLabel = document.getElementById("dash-scope-label");
const categoryChartEl = document.getElementById("category-chart");
const alertsListEl = document.getElementById("alerts-list");

const transactionsSection = document.getElementById("transactions-section");
const txScopeLabel = document.getElementById("tx-scope-label");
const transactionsTableBody = document.querySelector("#transactions-table tbody");

// ── Helpers ──────────────────────────────────────────────

function showStatus(message, type = "info") {
  statusEl.textContent = message;
  statusEl.className = `status-message ${type}`;
  statusEl.hidden = false;
}

function hideStatus() {
  statusEl.hidden = true;
}

function formatAmount(value) {
  const num = Number(value);
  if (isNaN(num)) return value;
  return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function clearTable(tbody) {
  tbody.innerHTML = "";
}

function formatDate(isoString) {
  if (!isoString) return "";
  const d = new Date(isoString);
  if (isNaN(d)) return isoString;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
    + " " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function getImportLabel(imp) {
  return imp.period_label || imp.file_name;
}

function getScopeLabel() {
  if (currentScope === "all") return "All imports";
  if (currentScope === "latest") {
    const latest = importsList[0];
    return latest ? `Latest — ${getImportLabel(latest)}` : "Latest import";
  }
  const imp = importsList.find((i) => i.id === currentScope);
  return imp ? getImportLabel(imp) : `Import #${currentScope}`;
}

function renderCategoryChart(categories) {
  if (!categoryChartEl) return;

  if (!categories || categories.length === 0) {
    categoryChartEl.innerHTML = '<p class="empty-state">No category data found.</p>';
    return;
  }

  const total = categories.reduce((sum, cat) => sum + cat.total_amount, 0);

  if (total === 0) {
    categoryChartEl.innerHTML = '<p class="empty-state">No category data found.</p>';
    return;
  }

  const colors = [
    "#1d4f91",
    "#0f9f75",
    "#f39c12",
    "#c0392b",
    "#8e44ad",
    "#16a085",
    "#d35400",
    "#7f8c8d",
    "#2c3e50",
  ];

  let cumulative = 0;
  const radius = 70;
  const circumference = 2 * Math.PI * radius;

  const segments = categories
    .map((cat, index) => {
      const fraction = cat.total_amount / total;
      const dash = fraction * circumference;
      const gap = circumference - dash;
      const offset = -cumulative * circumference;
      cumulative += fraction;

      return `
        <circle
          cx="90"
          cy="90"
          r="${radius}"
          fill="none"
          stroke="${colors[index % colors.length]}"
          stroke-width="28"
          stroke-dasharray="${dash} ${gap}"
          stroke-dashoffset="${offset}"
          transform="rotate(-90 90 90)"
        />
      `;
    })
    .join("");

  const legend = categories
    .map((cat, index) => {
      const percent = Math.round((cat.total_amount / total) * 100);
      return `
        <div class="category-legend-item">
          <span class="category-legend-label">
            <span class="category-legend-dot" style="background:${colors[index % colors.length]}"></span>
            ${cat.category_name}
          </span>
          <span class="category-legend-value">${percent}%</span>
        </div>
      `;
    })
    .join("");

  categoryChartEl.innerHTML = `
    <div class="category-chart-layout">
      <svg viewBox="0 0 180 180" class="category-chart-svg" aria-label="Spending by category chart">
        <circle cx="90" cy="90" r="${radius}" fill="none" stroke="#e5e7eb" stroke-width="28" />
        ${segments}
        <circle cx="90" cy="90" r="42" fill="#ffffff" />
      </svg>
      <div class="category-chart-legend">
        ${legend}
      </div>
    </div>
  `;
}

// ── Scope controls ───────────────────────────────────────

function updateScopeButtons() {
  scopeLatestBtn.classList.toggle("active", currentScope === "latest");
  scopeAllBtn.classList.toggle("active", currentScope === "all");
}

function setScope(scope) {
  currentScope = scope;
  updateScopeButtons();
  renderImportsList();
  loadScopedData();
}

scopeLatestBtn.addEventListener("click", () => setScope("latest"));
scopeAllBtn.addEventListener("click", () => setScope("all"));

// ── Event listeners (upload flow) ────────────────────────

fileInput.addEventListener("change", async () => {
  const hasFile = fileInput.files && fileInput.files.length > 0;

  previewData = null;
  previewSection.hidden = true;
  confirmBtn.disabled = true;
  clearTable(previewTableBody);
  hideStatus();

  await handlePreview();
});

confirmBtn.addEventListener("click", handleConfirm);
closePreviewBtn.addEventListener("click", () => {
  previewData = null;
  previewSection.hidden = true;
  confirmBtn.disabled = true;
  clearTable(previewTableBody);
  hideStatus();
});

// ── Preview ──────────────────────────────────────────────

async function handlePreview() {
  const file = fileInput.files[0];
  if (!file) return;

  confirmBtn.disabled = true;
  showStatus("Uploading and parsing file…", "info");

  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/imports/preview`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${res.status})`);
    }

    previewData = await res.json();
    renderPreview(previewData);
    showStatus("Preview ready — review transactions below, then confirm.", "success");
    confirmBtn.disabled = false;
  } catch (err) {
    showStatus(`Preview failed: ${err.message}`, "error");
    previewSection.hidden = true;
    previewData = null;
  }
}

function renderPreview(data) {
  previewFilename.textContent = data.filename;
  previewSkipped.textContent = data.skipped_rows_count;
  previewCount.textContent = data.transactions.length;

  clearTable(previewTableBody);
  data.transactions.forEach((tx) => {
    const row = previewTableBody.insertRow();
    row.insertCell().textContent = tx.transaction_date ?? "";
    row.insertCell().textContent = tx.merchant_name ?? "";
    row.insertCell().textContent = tx.category ?? "";
    const amountCell = row.insertCell();
    amountCell.textContent = formatAmount(tx.amount);
    amountCell.className = "amount";
    row.insertCell().textContent = tx.currency ?? "";
  });

  previewSection.hidden = false;
}

// ── Confirm ──────────────────────────────────────────────

async function handleConfirm() {
  if (!previewData) return;

  confirmBtn.disabled = true;
  showStatus("Confirming import…", "info");

  try {
    const res = await fetch(`${API_BASE}/imports/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: previewData.filename,
        file_hash: previewData.file_hash,
        transactions: previewData.transactions,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${res.status})`);
    }

    const result = await res.json();
    showStatus(
      `${result.message} — ${result.transactions_count} transaction(s) saved.`,
      "success"
    );

    previewData = null;
    previewSection.hidden = true;
    fileInput.value = "";
    confirmBtn.disabled = true;

    await loadImports();
    currentScope = result.import_id;
    updateScopeButtons();
    renderImportsList();
    await loadScopedData();
  } catch (err) {
    showStatus(`Import failed: ${err.message}`, "error");
    confirmBtn.disabled = false;
  }
}

// ── Imports list ─────────────────────────────────────────

async function loadImports() {
  try {
    const res = await fetch(`${API_BASE}/imports`);
    if (!res.ok) throw new Error(`Server error (${res.status})`);
    importsList = await res.json();
    renderImportsList();
    dashboardArea.hidden = false; // importsList.length === 0;
  } catch (err) {
    console.error("Failed to load imports:", err);
  }
}

function renderImportsList() {
  importsListEl.innerHTML = "";
  if (importsList.length === 0) {
    importsListEl.innerHTML = '<p class="empty-state">No imports yet.</p>';
    return;
  }

  importsList.forEach((imp) => {
    const isSelected = currentScope === imp.id;
    const item = document.createElement("div");
    item.className = "import-item" + (isSelected ? " selected" : "");
    const label = getImportLabel(imp);

    const info = document.createElement("div");
    info.className = "import-info";
    info.innerHTML =
      `<span class="import-name">${label}</span>` +
      `<span class="import-date">${formatDate(imp.imported_at)}</span>`;

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "import-delete-btn";
    deleteBtn.textContent = "\u00D7";
    deleteBtn.title = "Delete import";
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      handleDeleteImport(imp.id, label);
    });

    item.appendChild(info);
    item.appendChild(deleteBtn);
    item.addEventListener("click", () => setScope(imp.id));
    importsListEl.appendChild(item);
  });
}

async function handleDeleteImport(importId, label) {
  if (!confirm(`Delete "${label}" and all its transactions?`)) return;

  try {
    const res = await fetch(`${API_BASE}/imports/${importId}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${res.status})`);
    }

    const wasSelected = currentScope === importId;

    await loadImports();

    if (importsList.length === 0) {
      currentScope = "latest";
      dashboardArea.hidden = true;
      transactionsSection.hidden = true;

      dashTotalTx.textContent = "0";
      dashTotalAmt.textContent = "0";
      dashTopCategory.textContent = "—";
      dashTopCategoryMeta.textContent = "";
      dashScopeLabel.textContent = "";
      txScopeLabel.textContent = "";
      categoryChartEl.innerHTML = '<p class="empty-state">No category data found.</p>';
      clearTable(transactionsTableBody);
      alertsListEl.innerHTML = '<p class="empty-state">No insights found.</p>';
      return;
    }

    if (wasSelected) {
      currentScope = "latest";
    }

    updateScopeButtons();
    renderImportsList();
    await loadScopedData();
  } catch (err) {
    showStatus(`Delete failed: ${err.message}`, "error");
  }
}

// ── Load scoped dashboard + transactions ─────────────────

async function loadScopedData() {
  await Promise.all([loadDashboard(), loadTransactions()]);
}

async function loadDashboard() {
  try {
    let url = `${API_BASE}/dashboard`;
    if (typeof currentScope === "number") {
      url += `?import_id=${currentScope}`;
    } else {
      url += `?mode=${currentScope}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error(`Server error (${res.status})`);
    const data = await res.json();
    console.log("dashboard data", data);
    renderDashboard(data);
  } catch (err) {
    console.error("Failed to load dashboard:", err);
  }
}

function renderDashboard(data) {
  dashTotalTx.textContent = data.total_transactions;
  dashTotalAmt.textContent = formatAmount(data.total_amount);
  if (data.top_category) {
    dashTopCategory.textContent = data.top_category.category_name;
    dashTopCategoryMeta.textContent = `${formatAmount(data.top_category.total_amount)}  •  ${data.top_category.percent_of_spending}% of spending`;
  } else {
    dashTopCategory.textContent = "—";
    dashTopCategoryMeta.textContent = "";
  }
  dashScopeLabel.textContent = getScopeLabel();

  renderCategoryChart(data.spending_by_category);

  dashboardSection.hidden = false;

  alertsListEl.innerHTML = "";  // reset the card before rendering the current data fresh

  if (data.unusual_high_transactions && data.unusual_high_transactions.length > 0) {
    data.unusual_high_transactions.forEach((tx) => {
      const item = document.createElement("div");
      item.className = "alert-item";

      item.innerHTML = `
        <div class="alert-merchant">${tx.merchant_name}</div>
        <div class="alert-amounts">${formatAmount(tx.amount)}</div>
        <div class="alert-message">High transaction • ${tx.transaction_date}</div>
      `;

      alertsListEl.appendChild(item);
    });
  } else {
    alertsListEl.innerHTML = '<p class="empty-state">No insights found.</p>';
  }
}

async function loadTransactions() {
  try {
    let url = `${API_BASE}/transactions`;
    if (typeof currentScope === "number") {
      url += `?import_id=${currentScope}`;
    } else if (currentScope === "latest" && importsList.length > 0) {
      url += `?import_id=${importsList[0].id}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error(`Server error (${res.status})`);
    const data = await res.json();
    renderTransactions(data);
  } catch (err) {
    console.error("Failed to load transactions:", err);
  }
}

function renderTransactions(data) {
  clearTable(transactionsTableBody);
  txScopeLabel.textContent = getScopeLabel();

  data.forEach((tx) => {
    const row = transactionsTableBody.insertRow();
    row.insertCell().textContent = tx.transaction_date ?? "";
    row.insertCell().textContent = tx.merchant_name ?? "";
    row.insertCell().textContent = tx.category_name ?? "";
    const amtCell = row.insertCell();
    amtCell.textContent = formatAmount(tx.amount);
    amtCell.className = "amount";
    row.insertCell().textContent = tx.currency ?? "";
  });

  transactionsSection.hidden = false;
}

// ── Initial load ─────────────────────────────────────────

(async function init() {
  try {
    await loadImports();
    if (importsList.length > 0) {
      currentScope = "latest";
      updateScopeButtons();
      await loadScopedData();
    }
  } catch {
    // Backend might not be running yet
  }
})();