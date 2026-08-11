/**
 * ARC Asset Manager — application logic.
 * Wires up auth, dashboard table/filters/pagination, and the three modals
 * (Add/Edit Asset, CSV Bulk Upload, Sticker Preview) to the API client.
 */
(() => {
  // ---------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------
  const state = {
    page: 1,
    pageSize: 10,
    total: 0,
    editingAssetId: null,
    currentStickerObjectUrl: null,
  };

  // ---------------------------------------------------------------------
  // Element refs
  // ---------------------------------------------------------------------
  const authScreen = document.getElementById("auth-screen");
  const appShell = document.getElementById("app-shell");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  const loginSubmit = document.getElementById("login-submit");
  const userEmailEl = document.getElementById("user-email");
  const userAvatarEl = document.getElementById("user-avatar");
  const logoutBtn = document.getElementById("logout-btn");

  const assetTableBody = document.getElementById("asset-table-body");
  const colFilterBtns = document.querySelectorAll(".col-filter-btn");
  const colFilterInputs = document.querySelectorAll(".col-filter-input");
  const pageInfo = document.getElementById("page-info");
  const prevPageBtn = document.getElementById("prev-page");
  const nextPageBtn = document.getElementById("next-page");

  const addAssetBtn = document.getElementById("add-asset-btn");
  const bulkUploadBtn = document.getElementById("bulk-upload-btn");

  const assetModal = document.getElementById("asset-modal");
  const assetForm = document.getElementById("asset-form");
  const assetModalTitle = document.getElementById("asset-modal-title");
  const assetFormError = document.getElementById("asset-form-error");

  const csvModal = document.getElementById("csv-modal");
  const dropzone = document.getElementById("dropzone");
  const csvFileInput = document.getElementById("csv-file-input");
  const csvFileChip = document.getElementById("csv-file-chip");
  const csvUploadResult = document.getElementById("csv-upload-result");
  const csvUploadSubmit = document.getElementById("csv-upload-submit");
  const downloadSampleLink = document.getElementById("download-sample-csv");

  const stickerModal = document.getElementById("sticker-modal");
  const stickerImage = document.getElementById("sticker-image");
  const stickerSpinner = document.getElementById("sticker-spinner");
  const stickerPrintBtn = document.getElementById("sticker-print-btn");

  let pendingCsvFile = null;

  // ---------------------------------------------------------------------
  // Toasts
  // ---------------------------------------------------------------------
  function toast(message, type = "success") {
    const stack = document.getElementById("toast-stack");
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = message;
    stack.appendChild(el);
    setTimeout(() => el.remove(), 3500);
  }

  // ---------------------------------------------------------------------
  // Modal helpers
  // ---------------------------------------------------------------------
  function openModal(id) {
    document.getElementById(id).classList.remove("hidden");
  }
  function closeModal(id) {
    document.getElementById(id).classList.add("hidden");
  }
  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal(btn.dataset.closeModal));
  });
  document.querySelectorAll(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.classList.add("hidden");
    });
  });

  // ---------------------------------------------------------------------
  // Auth
  // ---------------------------------------------------------------------
  function showApp(email) {
    authScreen.classList.add("hidden");
    appShell.classList.remove("hidden");
    userEmailEl.textContent = email || "User";
    userAvatarEl.textContent = (email || "?").charAt(0).toUpperCase();
    loadAssets();
  }

  function showAuth() {
    appShell.classList.add("hidden");
    authScreen.classList.remove("hidden");
  }

  function decodeEmailFromToken(token) {
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.sub;
    } catch (_) {
      return null;
    }
  }

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    loginError.classList.add("hidden");
    loginSubmit.disabled = true;
    loginSubmit.textContent = "Signing in…";

    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;

    try {
      const { access_token } = await API.login(email, password);
      API.setToken(access_token);
      sessionStorage.setItem("arc_user_email", email);
      showApp(email);
      loginForm.reset();
    } catch (err) {
      loginError.textContent = err.message;
      loginError.classList.remove("hidden");
    } finally {
      loginSubmit.disabled = false;
      loginSubmit.textContent = "Log In";
    }
  });

  logoutBtn.addEventListener("click", () => {
    API.logout();
    sessionStorage.removeItem("arc_user_email");
    showAuth();
  });

  window.addEventListener("auth:expired", () => {
    toast("Session expired. Please log in again.", "error");
    showAuth();
  });

  // ---------------------------------------------------------------------
  // Dashboard: load & render assets
  // ---------------------------------------------------------------------
  async function loadAssets() {
    assetTableBody.innerHTML = `<tr class="loading-row"><td colspan="8">Loading assets…</td></tr>`;
    try {
      const data = await API.listAssets({
        page: state.page,
        page_size: state.pageSize,
      });
      state.total = data.total;
      renderTable(data.items);
      renderPagination();
    } catch (err) {
      assetTableBody.innerHTML = `<tr class="loading-row"><td colspan="8">Failed to load assets: ${escapeHtml(err.message)}</td></tr>`;
    }
  }

  function renderTable(items) {
    if (!items.length) {
      assetTableBody.innerHTML = `<tr><td colspan="8" class="empty-state">No assets found. Try adjusting your filters or add a new asset.</td></tr>`;
      return;
    }

    assetTableBody.innerHTML = items
      .map(
        (item) => `
      <tr data-id="${item.id}">
        <td>#${item.id}</td>
        <td><span class="badge">${escapeHtml(item.barcode_string)}</span></td>
        <td>${escapeHtml(item.assigned_name)}</td>
        <td>${renderHardwareCell(item)}</td>
        <td>${escapeHtml(item.country || "—")}</td>
        <td>${escapeHtml(item.city || "—")}</td>
        <td>${escapeHtml(item.asset_type || "—")}</td>
        <td>
          <div class="row-actions">
            <button class="clay-btn small edit-btn" data-id="${item.id}">Edit</button>
            <button class="clay-btn small primary sticker-btn" data-id="${item.id}">Sticker</button>
            <button class="clay-btn small danger delete-btn" data-id="${item.id}">Delete</button>
          </div>
        </td>
      </tr>`
      )
      .join("");

    assetTableBody.querySelectorAll(".edit-btn").forEach((btn) =>
      btn.addEventListener("click", () => openEditModal(Number(btn.dataset.id), items))
    );
    assetTableBody.querySelectorAll(".sticker-btn").forEach((btn) =>
      btn.addEventListener("click", () => openStickerModal(Number(btn.dataset.id)))
    );
    assetTableBody.querySelectorAll(".delete-btn").forEach((btn) =>
      btn.addEventListener("click", () => handleDelete(Number(btn.dataset.id)))
    );

    applyColumnFilters();
  }

  function renderPagination() {
    const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
    pageInfo.textContent = `Page ${state.page} of ${totalPages} (${state.total} assets)`;
    prevPageBtn.disabled = state.page <= 1;
    nextPageBtn.disabled = state.page >= totalPages;
  }

  prevPageBtn.addEventListener("click", () => {
    if (state.page > 1) {
      state.page -= 1;
      loadAssets();
    }
  });
  nextPageBtn.addEventListener("click", () => {
    state.page += 1;
    loadAssets();
  });

  // ---------------------------------------------------------------------
  // Per-column filters — pure DOM/client-side filtering of the currently
  // rendered table rows (no API calls). Each column header has a small
  // filter icon that toggles an inline text input; typing hides/shows rows.
  // ---------------------------------------------------------------------
  colFilterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.querySelector(`.col-filter-input[data-col="${btn.dataset.col}"]`);
      const willShow = input.classList.contains("hidden");
      input.classList.toggle("hidden", !willShow);
      btn.classList.toggle("active", willShow);
      if (willShow) input.focus();
    });
  });

  colFilterInputs.forEach((input) => {
    input.addEventListener("input", applyColumnFilters);
  });

  function applyColumnFilters() {
    const activeFilters = Array.from(colFilterInputs)
      .map((input) => ({ col: Number(input.dataset.col), value: input.value.trim().toLowerCase() }))
      .filter((f) => f.value !== "");

    const rows = assetTableBody.querySelectorAll("tr[data-id]");
    rows.forEach((row) => {
      const cells = row.children;
      const matches = activeFilters.every((f) => {
        const cellText = (cells[f.col]?.textContent || "").toLowerCase();
        return cellText.includes(f.value);
      });
      row.style.display = matches ? "" : "none";
    });
  }

  // ---------------------------------------------------------------------
  // Add / Edit Asset modal
  // ---------------------------------------------------------------------
  function resetAssetForm() {
    assetForm.reset();
    assetFormError.classList.add("hidden");
    state.editingAssetId = null;
  }

  addAssetBtn.addEventListener("click", () => {
    resetAssetForm();
    assetModalTitle.textContent = "Add Asset";
    openModal("asset-modal");
  });

  function openEditModal(id, items) {
    const asset = items.find((i) => i.id === id);
    if (!asset) return;
    resetAssetForm();
    state.editingAssetId = id;
    assetModalTitle.textContent = `Edit Asset #${id}`;
    document.getElementById("af-assigned-name").value = asset.assigned_name || "";
    document.getElementById("af-serial-number").value = asset.serial_number || "";
    document.getElementById("af-model").value = asset.model || "";
    document.getElementById("af-make").value = asset.make || "";
    document.getElementById("af-asset-type").value = asset.asset_type || "";
    document.getElementById("af-country").value = asset.country || "";
    document.getElementById("af-city").value = asset.city || "";
    openModal("asset-modal");
  }

  assetForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    assetFormError.classList.add("hidden");

    const payload = {
      assigned_name: document.getElementById("af-assigned-name").value.trim(),
      serial_number: document.getElementById("af-serial-number").value.trim(),
      model: document.getElementById("af-model").value.trim() || null,
      make: document.getElementById("af-make").value.trim() || null,
      asset_type: document.getElementById("af-asset-type").value.trim() || null,
      country: document.getElementById("af-country").value.trim() || null,
      city: document.getElementById("af-city").value.trim() || null,
    };

    const submitBtn = document.getElementById("asset-form-submit");
    submitBtn.disabled = true;
    submitBtn.textContent = "Saving…";

    try {
      if (state.editingAssetId) {
        await API.updateAsset(state.editingAssetId, payload);
        toast("Asset updated successfully.");
      } else {
        await API.createAsset(payload);
        toast("Asset created successfully.");
      }
      closeModal("asset-modal");
      loadAssets();
    } catch (err) {
      assetFormError.textContent = err.message;
      assetFormError.classList.remove("hidden");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Save Asset";
    }
  });

  async function handleDelete(id) {
    if (!confirm(`Delete asset #${id}? This cannot be undone.`)) return;
    try {
      await API.deleteAsset(id);
      toast("Asset deleted.");
      loadAssets();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  // ---------------------------------------------------------------------
  // CSV Bulk Upload modal
  // ---------------------------------------------------------------------
  const SAMPLE_CSV = "assigned_name,serial_number,model,make,country,city,asset_type\nJane Smith,SN-1001,X2,HP,India,Kolkata,Laptop\nBob Lee,SN-1002,X3,Lenovo,India,Mumbai,Desktop\n";
  downloadSampleLink.href = URL.createObjectURL(new Blob([SAMPLE_CSV], { type: "text/csv" }));

  bulkUploadBtn.addEventListener("click", () => {
    resetCsvModal();
    openModal("csv-modal");
  });

  function resetCsvModal() {
    pendingCsvFile = null;
    csvFileInput.value = "";
    csvFileChip.classList.add("hidden");
    csvUploadResult.classList.add("hidden");
    csvUploadSubmit.disabled = true;
    dropzone.classList.remove("dragover");
  }

  function selectCsvFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      toast("Please select a .csv file.", "error");
      return;
    }
    pendingCsvFile = file;
    csvFileChip.textContent = `📄 ${file.name}`;
    csvFileChip.classList.remove("hidden");
    csvUploadSubmit.disabled = false;
  }

  dropzone.addEventListener("click", () => csvFileInput.click());
  csvFileInput.addEventListener("change", () => selectCsvFile(csvFileInput.files[0]));

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    selectCsvFile(file);
  });

  csvUploadSubmit.addEventListener("click", async () => {
    if (!pendingCsvFile) return;
    csvUploadSubmit.disabled = true;
    csvUploadSubmit.textContent = "Uploading…";
    csvUploadResult.classList.add("hidden");

    try {
      const result = await API.uploadCsv(pendingCsvFile);
      const isSuccess = result.skipped === 0;
      csvUploadResult.className = `upload-result ${isSuccess ? "success" : "error"}`;
      csvUploadResult.innerHTML = `<strong>${result.inserted} inserted, ${result.skipped} skipped.</strong>` +
        (result.errors && result.errors.length
          ? `<ul>${result.errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul>`
          : "");
      csvUploadResult.classList.remove("hidden");
      toast(`Upload complete: ${result.inserted} asset(s) added.`);
      loadAssets();
    } catch (err) {
      csvUploadResult.className = "upload-result error";
      csvUploadResult.textContent = err.message;
      csvUploadResult.classList.remove("hidden");
    } finally {
      csvUploadSubmit.disabled = false;
      csvUploadSubmit.textContent = "Upload";
    }
  });

  // ---------------------------------------------------------------------
  // Sticker Preview modal
  // ---------------------------------------------------------------------
  async function openStickerModal(id) {
    stickerImage.classList.add("hidden");
    stickerSpinner.classList.remove("hidden");
    openModal("sticker-modal");

    if (state.currentStickerObjectUrl) {
      URL.revokeObjectURL(state.currentStickerObjectUrl);
      state.currentStickerObjectUrl = null;
    }

    try {
      const objectUrl = await API.fetchSticker(id);
      state.currentStickerObjectUrl = objectUrl;
      stickerImage.src = objectUrl;
      stickerImage.classList.remove("hidden");
    } catch (err) {
      toast(err.message, "error");
      closeModal("sticker-modal");
    } finally {
      stickerSpinner.classList.add("hidden");
    }
  }

  stickerPrintBtn.addEventListener("click", () => {
    if (!stickerImage.src) return;
    const printWindow = window.open("", "_blank");
    printWindow.document.write(`
      <html><head><title>Print Sticker</title>
      <style>body{margin:0;display:flex;align-items:center;justify-content:center;height:100vh;} img{max-width:100%;}</style>
      </head><body><img src="${stickerImage.src}" onload="window.print(); window.close();" /></body></html>
    `);
    printWindow.document.close();
  });

  // ---------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------
  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** Renders the "Hardware" column: make + model on one line, serial below. */
  function renderHardwareCell(item) {
    const makeModel = [item.make, item.model].filter(Boolean).join(" ") || "—";
    return `
      <div class="hardware-cell">
        <span class="hw-make-model">${escapeHtml(makeModel)}</span>
        <span class="hw-serial">SN: ${escapeHtml(item.serial_number)}</span>
      </div>
    `;
  }

  // ---------------------------------------------------------------------
  // Bootstrap
  // ---------------------------------------------------------------------
  if (API.isAuthenticated()) {
    const email = sessionStorage.getItem("arc_user_email") || decodeEmailFromToken(API.getToken());
    showApp(email);
  } else {
    showAuth();
  }
})();
