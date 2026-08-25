/**
 * Sign Scanner Pro - Interactive Web UI Controller
 * Includes PDF Generator & Smart Signature Extractor
 */

// Application State
const state = {
  // Navigation
  activeModule: 'extractor', // 'extractor' | 'generator'

  // Generator State
  employees: [],
  filteredEmployees: [],

  // Extractor State
  scans: [],
  selectedScan: null,
  imageWidth: 0,
  imageHeight: 0,
  items: [],
  selectedItemId: null,
  zoom: 1.0,
  panX: 0,
  panY: 0,
  tool: 'select', // 'select' | 'draw'
  showQr: true,
  isDrawing: false,
  drawStart: null,
  isDraggingBox: false,
  isResizingBox: false,
  activeHandle: null,
  dragStartPos: null,
  boxStartRect: null,
  previewDebounceTimer: null,
  activeTab: 'trans' // 'trans' | 'raw'
};

// DOM Elements
const elements = {
  // Navigation Tabs
  navTabGenerate: document.getElementById('navTabGenerate'),
  navTabExtract: document.getElementById('navTabExtract'),
  viewGenerator: document.getElementById('view-generator'),
  viewExtractor: document.getElementById('view-extractor'),
  extractorHeaderActions: document.getElementById('extractorHeaderActions'),

  // Generator Elements
  fileCsvInput: document.getElementById('fileCsvInput'),
  btnUploadCsv: document.getElementById('btnUploadCsv'),
  btnResetSample: document.getElementById('btnResetSample'),
  btnGeneratePdf: document.getElementById('btnGeneratePdf'),
  pdfSuccessCard: document.getElementById('pdfSuccessCard'),
  btnDownloadPdf: document.getElementById('btnDownloadPdf'),
  genEmpCount: document.getElementById('genEmpCount'),
  genDeptCount: document.getElementById('genDeptCount'),
  genPageCount: document.getElementById('genPageCount'),
  addEmpCode: document.getElementById('addEmpCode'),
  addEmpName: document.getElementById('addEmpName'),
  addEmpDept: document.getElementById('addEmpDept'),
  btnAddEmployee: document.getElementById('btnAddEmployee'),
  searchEmpTable: document.getElementById('searchEmpTable'),
  btnClearTable: document.getElementById('btnClearTable'),
  employeesTableBody: document.getElementById('employeesTableBody'),

  // Extractor Elements
  scanSelect: document.getElementById('scanSelect'),
  detectMethodSelect: document.getElementById('detectMethodSelect'),
  btnReloadScans: document.getElementById('btnReloadScans'),
  btnDetect: document.getElementById('btnDetect'),
  btnSaveAll: document.getElementById('btnSaveAll'),
  btnAddBox: document.getElementById('btnAddBox'),
  itemsContainer: document.getElementById('itemsContainer'),
  itemCount: document.getElementById('itemCount'),
  btnZoomIn: document.getElementById('btnZoomIn'),
  btnZoomOut: document.getElementById('btnZoomOut'),
  btnZoomFit: document.getElementById('btnZoomFit'),
  btnZoom100: document.getElementById('btnZoom100'),
  zoomLevel: document.getElementById('zoomLevel'),
  btnToolSelect: document.getElementById('btnToolSelect'),
  btnToolDraw: document.getElementById('btnToolDraw'),
  chkShowQr: document.getElementById('chkShowQr'),
  canvasScrollArea: document.getElementById('canvasScrollArea'),
  canvasWrapper: document.getElementById('canvasWrapper'),
  documentImage: document.getElementById('documentImage'),
  overlayCanvas: document.getElementById('overlayCanvas'),
  boxHandlesLayer: document.getElementById('boxHandlesLayer'),
  statusMessage: document.getElementById('statusMessage'),
  inputEmpCode: document.getElementById('inputEmpCode'),
  coordsDisplay: document.getElementById('coordsDisplay'),
  previewTabs: document.querySelectorAll('.preview-tab'),
  imgTransPreview: document.getElementById('imgTransPreview'),
  imgRawPreview: document.getElementById('imgRawPreview'),
  previewLoader: document.getElementById('previewLoader'),
  rangeThreshold: document.getElementById('rangeThreshold'),
  valThreshold: document.getElementById('valThreshold'),
  rangePadding: document.getElementById('rangePadding'),
  valPadding: document.getElementById('valPadding'),
  btnApplyAllThreshold: document.getElementById('btnApplyAllThreshold'),
  btnSaveSingle: document.getElementById('btnSaveSingle'),
  btnDeleteBox: document.getElementById('btnDeleteBox'),
  toastContainer: document.getElementById('toastContainer')
};

// Toast Notifications
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function setStatus(msg) {
  if (elements.statusMessage) elements.statusMessage.textContent = msg;
}

/* ================= NAVIGATION TABS ================= */
function switchModule(target) {
  state.activeModule = target;
  if (target === 'generator') {
    elements.navTabGenerate.classList.add('active');
    elements.navTabExtract.classList.remove('active');
    elements.viewGenerator.style.display = 'block';
    elements.viewExtractor.style.display = 'none';
    elements.extractorHeaderActions.style.display = 'none';
    if (state.employees.length === 0) {
      fetchEmployeesData();
    }
  } else {
    elements.navTabExtract.classList.add('active');
    elements.navTabGenerate.classList.remove('active');
    elements.viewExtractor.style.display = 'flex';
    elements.viewGenerator.style.display = 'none';
    elements.extractorHeaderActions.style.display = 'flex';
    setTimeout(resizeCanvas, 50);
  }
}

elements.navTabGenerate.addEventListener('click', () => switchModule('generator'));
elements.navTabExtract.addEventListener('click', () => switchModule('extractor'));

/* ================= MODULE 1: PDF GENERATOR LOGIC ================= */
async function fetchEmployeesData() {
  try {
    const res = await fetch('/api/employees-data');
    const data = await res.json();
    if (data.employees) {
      state.employees = data.employees;
      state.filteredEmployees = [...state.employees];
      renderEmployeesTable();
      updateGeneratorStats();
    }
  } catch (err) {
    showToast('خطا در دریافت لیست پرسنل', 'error');
  }
}

function updateGeneratorStats() {
  const count = state.employees.length;
  const depts = new Set(state.employees.map(e => e.dept).filter(Boolean));
  
  // Calculate pages (12 per page, grouped by dept)
  let pages = 0;
  let currentDept = null;
  let inDeptCount = 0;
  
  const sorted = [...state.employees];
  sorted.forEach(e => {
    if (e.dept !== currentDept) {
      currentDept = e.dept;
      inDeptCount = 0;
      pages++;
    }
    inDeptCount++;
    if (inDeptCount > 12) {
      pages++;
      inDeptCount = 1;
    }
  });

  elements.genEmpCount.textContent = count.toLocaleString('fa-IR');
  elements.genDeptCount.textContent = depts.size.toLocaleString('fa-IR');
  elements.genPageCount.textContent = (pages || (count > 0 ? 1 : 0)).toLocaleString('fa-IR');
}

function renderEmployeesTable() {
  const tbody = elements.employeesTableBody;
  tbody.innerHTML = '';

  const list = state.filteredEmployees;
  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="table-loading">هیچ پرسنلی یافت نشد.</td></tr>`;
    return;
  }

  list.forEach((emp, index) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="text-align: center; color: var(--text-dim);">${(index + 1).toLocaleString('fa-IR')}</td>
      <td>
        <input type="text" class="table-input" value="${emp.empCode}" data-index="${index}" data-field="empCode" />
      </td>
      <td>
        <input type="text" class="table-input" value="${emp.name}" data-index="${index}" data-field="name" />
      </td>
      <td>
        <input type="text" class="table-input" value="${emp.dept}" data-index="${index}" data-field="dept" />
      </td>
      <td style="text-align: center;">
        <button class="btn btn-danger btn-xs btn-delete-emp" data-index="${index}">🗑️</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Attach change listeners
  tbody.querySelectorAll('.table-input').forEach(input => {
    input.addEventListener('change', (e) => {
      const idx = parseInt(e.target.dataset.index);
      const field = e.target.dataset.field;
      state.filteredEmployees[idx][field] = e.target.value;
      updateGeneratorStats();
    });
  });

  tbody.querySelectorAll('.btn-delete-emp').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const idx = parseInt(btn.dataset.index);
      state.employees.splice(idx, 1);
      state.filteredEmployees = [...state.employees];
      renderEmployeesTable();
      updateGeneratorStats();
    });
  });
}

// Search Filter
elements.searchEmpTable.addEventListener('input', (e) => {
  const q = e.target.value.toLowerCase().trim();
  if (!q) {
    state.filteredEmployees = [...state.employees];
  } else {
    state.filteredEmployees = state.employees.filter(emp => 
      emp.empCode.toLowerCase().includes(q) ||
      emp.name.toLowerCase().includes(q) ||
      emp.dept.toLowerCase().includes(q)
    );
  }
  renderEmployeesTable();
});

// Clear Table
elements.btnClearTable.addEventListener('click', () => {
  if (confirm('آیا از پاکسازی تمام ردیف‌های جدول پرسنل اطمینان دارید؟')) {
    state.employees = [];
    state.filteredEmployees = [];
    renderEmployeesTable();
    updateGeneratorStats();
    showToast('جدول پاکسازی شد', 'info');
  }
});

// Add Employee
elements.btnAddEmployee.addEventListener('click', () => {
  const code = elements.addEmpCode.value.trim();
  const name = elements.addEmpName.value.trim();
  const dept = elements.addEmpDept.value.trim();

  if (!code) {
    showToast('لطفاً کد پرسنلی را وارد کنید', 'error');
    return;
  }

  state.employees.unshift({
    empCode: code,
    name: name || 'بدون نام',
    dept: dept || 'عمومی'
  });
  state.filteredEmployees = [...state.employees];
  renderEmployeesTable();
  updateGeneratorStats();

  elements.addEmpCode.value = '';
  elements.addEmpName.value = '';
  showToast(`پرسنل با کد ${code} افزوده شد`, 'success');
});

// Upload CSV
elements.btnUploadCsv.addEventListener('click', () => {
  elements.fileCsvInput.click();
});

elements.fileCsvInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (event) => {
    const csvContent = event.target.result;
    try {
      const res = await fetch('/api/upload-csv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: csvContent })
      });
      const data = await res.json();
      if (data.success && data.employees) {
        state.employees = data.employees;
        state.filteredEmployees = [...state.employees];
        renderEmployeesTable();
        updateGeneratorStats();
        showToast(`تعداد ${data.total} پرسنل از فایل بارگذاری شد`, 'success');
      } else {
        showToast(data.error || 'خطا در بارگذاری فایل CSV', 'error');
      }
    } catch (err) {
      showToast('خطا در ارتباط با سرور', 'error');
    }
  };
  reader.readAsText(file);
});

// Reset Sample
elements.btnResetSample.addEventListener('click', () => {
  fetchEmployeesData();
  showToast('داده‌های نمونه بازنشانی شدند', 'info');
});

// Generate PDF
elements.btnGeneratePdf.addEventListener('click', async () => {
  if (state.employees.length === 0) {
    showToast('هیچ پرسنلی در جدول برای تولید برگه وجود ندارد', 'error');
    return;
  }

  showToast('در حال تولید فایل PDF برگه امضا...', 'info');
  elements.btnGeneratePdf.disabled = true;

  try {
    const res = await fetch('/api/generate-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ employees: state.employees })
    });
    const data = await res.json();
    if (data.success) {
      showToast('🎉 فایل PDF برگه امضا با موفقیت ساخته شد!', 'success');
      elements.pdfSuccessCard.style.display = 'flex';
      elements.btnDownloadPdf.href = data.downloadUrl || '/api/download-pdf';
    } else {
      showToast(data.error || 'خطا در تولید PDF', 'error');
    }
  } catch (err) {
    showToast('خطا در ارتباط با سرور هنگام ساخت PDF', 'error');
  } finally {
    elements.btnGeneratePdf.disabled = false;
  }
});


/* ================= MODULE 2: EXTRACTOR LOGIC ================= */
async function fetchScans() {
  try {
    const res = await fetch('/api/scans');
    const data = await res.json();
    state.scans = data.scans || [];
    renderScanOptions();
  } catch (err) {
    showToast('خطا در دریافت لیست اسکن‌ها', 'error');
  }
}

function renderScanOptions() {
  elements.scanSelect.innerHTML = '';
  if (state.scans.length === 0) {
    elements.scanSelect.innerHTML = '<option value="">هیچ فایلی در پوشه scans یافت نشد</option>';
    return;
  }

  state.scans.forEach((scan, index) => {
    const opt = document.createElement('option');
    opt.value = scan.name;
    opt.textContent = `${index + 1}. ${scan.name} (${(scan.size / 1024).toFixed(1)} KB)`;
    elements.scanSelect.appendChild(opt);
  });

  if (!state.selectedScan && state.scans.length > 0) {
    selectScan(state.scans[0].name);
  }
}

async function selectScan(filename) {
  if (!filename) return;
  state.selectedScan = filename;
  state.items = [];
  state.selectedItemId = null;
  renderItemsList();
  clearPreview();

  setStatus(`در حال بارگذاری تصویر ${filename}...`);
  elements.documentImage.onerror = () => {
    setStatus(`خطا در بارگذاری تصویر ${filename}`);
    showToast(`عدم دسترسی به فایل تصویر ${filename}`, 'error');
  };
  elements.documentImage.onload = () => {
    state.imageWidth = elements.documentImage.naturalWidth;
    state.imageHeight = elements.documentImage.naturalHeight;
    elements.documentImage.style.width = `${state.imageWidth}px`;
    elements.documentImage.style.height = `${state.imageHeight}px`;
    resizeCanvas();
    zoomFit();
    setStatus(`تصویر بارگذاری شد: ${state.imageWidth}×${state.imageHeight} پیکسل - برای تشخیص روی «تشخیص هوشمند» کلیک کنید`);
  };
  elements.documentImage.src = `/api/scan-image?file=${encodeURIComponent(filename)}&t=${Date.now()}`;
}

async function detectBoxes() {
  if (!state.selectedScan) return;
  const method = elements.detectMethodSelect ? elements.detectMethodSelect.value : 'smart';
  const methodLabel = elements.detectMethodSelect ? elements.detectMethodSelect.options[elements.detectMethodSelect.selectedIndex].text : '';

  setStatus(`در حال آنالیز (${methodLabel})...`);
  showToast('در حال اسکن و تشخیص کادرها با متد انتخابی...', 'info');

  try {
    const res = await fetch('/api/detect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: state.selectedScan, method: method })
    });
    const data = await res.json();

    if (data.error) {
      showToast(data.error, 'error');
      setStatus('خطا در تشخیص');
      return;
    }

    state.items = data.items || [];
    renderItemsList();
    renderOverlay();
    
    const timeStr = data.elapsedMs ? ` (زمان: ${data.elapsedMs} میلی‌ثانیه)` : '';
    setStatus(`تشخیص انجام شد: ${data.totalQrFound} بارکد و ${data.totalBoxesFound} کادر امضا${timeStr}`);
    showToast(`تعداد ${state.items.length} کادر امضا شناسایی شد${timeStr}`, 'success');

    if (state.items.length > 0) {
      selectItem(state.items[0].id);
    }
  } catch (err) {
    showToast('خطا در ارتباط با سرور هنگام تشخیص', 'error');
  }
}

function resizeCanvas() {
  const img = elements.documentImage;
  const canvas = elements.overlayCanvas;
  const wrapper = elements.canvasWrapper;

  if (!img.naturalWidth) return;

  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  wrapper.style.width = `${img.naturalWidth}px`;
  wrapper.style.height = `${img.naturalHeight}px`;

  renderOverlay();
}

function updateZoom(newZoom) {
  state.zoom = Math.max(0.15, Math.min(3.5, newZoom));
  elements.zoomLevel.textContent = `${Math.round(state.zoom * 100)}%`;
  elements.canvasWrapper.style.transform = `scale(${state.zoom})`;
}

function zoomFit() {
  const container = elements.canvasScrollArea;
  if (!state.imageWidth) return;
  const scaleX = (container.clientWidth - 40) / state.imageWidth;
  const scaleY = (container.clientHeight - 40) / state.imageHeight;
  updateZoom(Math.min(scaleX, scaleY, 1.0));
}

// Rendering Items
function renderItemsList() {
  elements.itemsContainer.innerHTML = '';
  elements.itemCount.textContent = state.items.length;

  if (state.items.length === 0) {
    elements.itemsContainer.innerHTML = `
      <div class="empty-state">
        <p>هیچ کادری شناسایی نشده است.</p>
        <span>دکمه «تشخیص خودکار» یا «کادر جدید» را بزنید.</span>
      </div>`;
    return;
  }

  state.items.forEach((item, index) => {
    const card = document.createElement('div');
    card.className = `item-card ${item.id === state.selectedItemId ? 'active' : ''}`;
    card.dataset.id = item.id;

    const isAuto = item.matchedType === 'box_contour';
    card.innerHTML = `
      <div class="item-card-info">
        <span class="item-code">${item.empCode || 'نامشخص'}</span>
        <span class="item-status">${(index + 1)}. کادر برش امضا</span>
      </div>
      <span class="badge ${isAuto ? 'badge-auto' : 'badge-manual'}">
        ${isAuto ? 'خودکار' : 'تنظیم'}
      </span>
    `;

    card.addEventListener('click', () => selectItem(item.id));
    elements.itemsContainer.appendChild(card);
  });
}

function selectItem(id) {
  state.selectedItemId = id;
  const item = state.items.find((i) => i.id === id);

  document.querySelectorAll('.item-card').forEach((c) => {
    c.classList.toggle('active', c.dataset.id === id);
  });

  if (!item) {
    clearPreview();
    renderOverlay();
    return;
  }

  elements.inputEmpCode.value = item.empCode || '';
  elements.rangeThreshold.value = item.threshold || 200;
  elements.valThreshold.textContent = item.threshold || 200;
  elements.rangePadding.value = item.padding !== undefined ? item.padding : 6;
  elements.valPadding.textContent = `${elements.rangePadding.value}px`;

  const r = item.cropRect;
  elements.coordsDisplay.textContent = `X: ${r.x}, Y: ${r.y} (${r.w}×${r.h})`;

  renderOverlay();
  triggerCropPreview();
}

function clearPreview() {
  elements.imgTransPreview.src = '';
  elements.imgRawPreview.src = '';
  elements.coordsDisplay.textContent = 'X: 0, Y: 0 (0x0)';
  elements.inputEmpCode.value = '';
}

function renderOverlay() {
  const canvas = elements.overlayCanvas;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  elements.boxHandlesLayer.innerHTML = '';

  state.items.forEach((item) => {
    const isSelected = item.id === state.selectedItemId;
    const r = item.cropRect;

    // Draw QR Box if available and enabled
    if (state.showQr && item.qrRect) {
      const qr = item.qrRect;
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.8)';
      ctx.lineWidth = 2;
      ctx.strokeRect(qr.x, qr.y, qr.w, qr.h);
      ctx.fillStyle = 'rgba(56, 189, 248, 0.15)';
      ctx.fillRect(qr.x, qr.y, qr.w, qr.h);
    }

    // Draw Crop Box
    ctx.lineWidth = isSelected ? 3 : 2;
    ctx.strokeStyle = isSelected ? '#f59e0b' : '#10b981';
    ctx.fillStyle = isSelected ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.08)';

    ctx.fillRect(r.x, r.y, r.w, r.h);
    ctx.strokeRect(r.x, r.y, r.w, r.h);

    // Draw Employee Code Tag
    ctx.font = 'bold 14px JetBrains Mono, Vazirmatn, sans-serif';
    const tagText = ` ${item.empCode} `;
    const textW = ctx.measureText(tagText).width;
    ctx.fillStyle = isSelected ? '#f59e0b' : '#10b981';
    ctx.fillRect(r.x, r.y - 20, textW + 6, 20);
    ctx.fillStyle = '#000000';
    ctx.fillText(tagText, r.x + 3, r.y - 5);

    // If selected, render interactive handles
    if (isSelected) {
      renderHandles(item);
    }
  });
}

function renderHandles(item) {
  const layer = elements.boxHandlesLayer;
  layer.innerHTML = '';
  const r = item.cropRect;

  const handles = [
    { type: 'nw', x: r.x, y: r.y },
    { type: 'ne', x: r.x + r.w, y: r.y },
    { type: 'se', x: r.x + r.w, y: r.y + r.h },
    { type: 'sw', x: r.x, y: r.y + r.h }
  ];

  handles.forEach((h) => {
    const el = document.createElement('div');
    el.className = `box-handle ${h.type}`;
    el.style.left = `${h.x}px`;
    el.style.top = `${h.y}px`;
    el.dataset.handle = h.type;
    layer.appendChild(el);
  });
}

function triggerCropPreview() {
  clearTimeout(state.previewDebounceTimer);
  state.previewDebounceTimer = setTimeout(async () => {
    const item = state.items.find((i) => i.id === state.selectedItemId);
    if (!item || !state.selectedScan) return;

    elements.previewLoader.style.display = 'flex';

    try {
      const res = await fetch('/api/preview-crop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: state.selectedScan,
          rect: item.cropRect,
          threshold: item.threshold || 200,
          padding: item.padding !== undefined ? item.padding : 6
        })
      });
      const data = await res.json();
      if (data.rawImage && data.transparentImage) {
        elements.imgRawPreview.src = data.rawImage;
        elements.imgTransPreview.src = data.transparentImage;
      }
    } catch (err) {
      console.error(err);
    } finally {
      elements.previewLoader.style.display = 'none';
    }
  }, 120);
}

// Canvas Mouse Interactions
function getCanvasCoords(e) {
  const rect = elements.overlayCanvas.getBoundingClientRect();
  const clientX = e.clientX;
  const clientY = e.clientY;
  const x = Math.round((clientX - rect.left) / state.zoom);
  const y = Math.round((clientY - rect.top) / state.zoom);
  return { x, y };
}

elements.canvasScrollArea.addEventListener('mousedown', (e) => {
  if (e.target.classList.contains('box-handle')) {
    state.isResizingBox = true;
    state.activeHandle = e.target.dataset.handle;
    state.dragStartPos = getCanvasCoords(e);
    const item = state.items.find((i) => i.id === state.selectedItemId);
    state.boxStartRect = { ...item.cropRect };
    e.stopPropagation();
    return;
  }

  const { x, y } = getCanvasCoords(e);

  if (state.tool === 'draw') {
    state.isDrawing = true;
    state.drawStart = { x, y };
    return;
  }

  // Click on existing box to select / drag
  const clickedItem = [...state.items].reverse().find((item) => {
    const r = item.cropRect;
    return x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h;
  });

  if (clickedItem) {
    selectItem(clickedItem.id);
    state.isDraggingBox = true;
    state.dragStartPos = { x, y };
    state.boxStartRect = { ...clickedItem.cropRect };
  }
});

window.addEventListener('mousemove', (e) => {
  const { x, y } = getCanvasCoords(e);

  if (state.isResizingBox && state.selectedItemId) {
    const item = state.items.find((i) => i.id === state.selectedItemId);
    const orig = state.boxStartRect;
    const dx = x - state.dragStartPos.x;
    const dy = y - state.dragStartPos.y;

    if (state.activeHandle === 'se') {
      item.cropRect.w = Math.max(20, orig.w + dx);
      item.cropRect.h = Math.max(20, orig.h + dy);
    } else if (state.activeHandle === 'sw') {
      item.cropRect.x = orig.x + dx;
      item.cropRect.w = Math.max(20, orig.w - dx);
      item.cropRect.h = Math.max(20, orig.h + dy);
    } else if (state.activeHandle === 'ne') {
      item.cropRect.y = orig.y + dy;
      item.cropRect.w = Math.max(20, orig.w + dx);
      item.cropRect.h = Math.max(20, orig.h - dy);
    } else if (state.activeHandle === 'nw') {
      item.cropRect.x = orig.x + dx;
      item.cropRect.y = orig.y + dy;
      item.cropRect.w = Math.max(20, orig.w - dx);
      item.cropRect.h = Math.max(20, orig.h - dy);
    }

    elements.coordsDisplay.textContent = `X: ${item.cropRect.x}, Y: ${item.cropRect.y} (${item.cropRect.w}×${item.cropRect.h})`;
    renderOverlay();
    triggerCropPreview();
    return;
  }

  if (state.isDraggingBox && state.selectedItemId) {
    const item = state.items.find((i) => i.id === state.selectedItemId);
    const dx = x - state.dragStartPos.x;
    const dy = y - state.dragStartPos.y;

    item.cropRect.x = Math.max(0, state.boxStartRect.x + dx);
    item.cropRect.y = Math.max(0, state.boxStartRect.y + dy);

    elements.coordsDisplay.textContent = `X: ${item.cropRect.x}, Y: ${item.cropRect.y} (${item.cropRect.w}×${item.cropRect.h})`;
    renderOverlay();
    triggerCropPreview();
    return;
  }

  if (state.isDrawing && state.drawStart) {
    const canvas = elements.overlayCanvas;
    const ctx = canvas.getContext('2d');
    renderOverlay();

    const rx = Math.min(state.drawStart.x, x);
    const ry = Math.min(state.drawStart.y, y);
    const rw = Math.abs(x - state.drawStart.x);
    const rh = Math.abs(y - state.drawStart.y);

    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.strokeRect(rx, ry, rw, rh);
    ctx.setLineDash([]);
  }
});

window.addEventListener('mouseup', (e) => {
  if (state.isResizingBox) state.isResizingBox = false;
  if (state.isDraggingBox) state.isDraggingBox = false;

  if (state.isDrawing && state.drawStart) {
    state.isDrawing = false;
    const { x, y } = getCanvasCoords(e);
    const rx = Math.min(state.drawStart.x, x);
    const ry = Math.min(state.drawStart.y, y);
    const rw = Math.abs(x - state.drawStart.x);
    const rh = Math.abs(y - state.drawStart.y);

    if (rw > 25 && rh > 25) {
      const newId = `custom_${Date.now()}`;
      const newItem = {
        id: newId,
        empCode: `EMP_${state.items.length + 1}`,
        qrRect: null,
        cropRect: { x: rx, y: ry, w: rw, h: rh },
        matchedType: 'manual',
        threshold: 200,
        padding: 6,
        confirmed: true
      };
      state.items.push(newItem);
      renderItemsList();
      selectItem(newId);
      showToast('کادر جدید افزوده شد', 'success');
    }
    state.drawStart = null;
    setTool('select');
  }
});

// Tool Switching
function setTool(tool) {
  state.tool = tool;
  elements.btnToolSelect.classList.toggle('active', tool === 'select');
  elements.btnToolDraw.classList.toggle('active', tool === 'draw');
  elements.canvasScrollArea.style.cursor = tool === 'draw' ? 'crosshair' : 'grab';
}

elements.btnToolSelect.addEventListener('click', () => setTool('select'));
elements.btnToolDraw.addEventListener('click', () => setTool('draw'));

// Zoom Buttons
elements.btnZoomIn.addEventListener('click', () => updateZoom(state.zoom + 0.15));
elements.btnZoomOut.addEventListener('click', () => updateZoom(state.zoom - 0.15));
elements.btnZoomFit.addEventListener('click', zoomFit);
elements.btnZoom100.addEventListener('click', () => updateZoom(1.0));

// Canvas Wheel Zoom
elements.canvasScrollArea.addEventListener(
  'wheel',
  (e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY < 0 ? 0.1 : -0.1;
      updateZoom(state.zoom + delta);
    }
  },
  { passive: false }
);

// Toggle QR Display
elements.chkShowQr.addEventListener('change', (e) => {
  state.showQr = e.target.checked;
  renderOverlay();
});

// Scan Select & Reload
elements.scanSelect.addEventListener('change', (e) => {
  selectScan(e.target.value);
});

elements.btnReloadScans.addEventListener('click', () => {
  fetchScans();
  showToast('لیست اسکن‌ها بروزرسانی شد', 'info');
});

elements.btnDetect.addEventListener('click', () => {
  detectBoxes();
});

elements.btnAddBox.addEventListener('click', () => {
  setTool('draw');
  showToast('حالا روی تصویر کادر مورد نظر را رسم کنید', 'info');
});

// Inputs and Adjustments
elements.inputEmpCode.addEventListener('input', (e) => {
  const item = state.items.find((i) => i.id === state.selectedItemId);
  if (item) {
    item.empCode = e.target.value.trim();
    renderItemsList();
    renderOverlay();
  }
});

elements.rangeThreshold.addEventListener('input', (e) => {
  const val = parseInt(e.target.value);
  elements.valThreshold.textContent = val;
  const item = state.items.find((i) => i.id === state.selectedItemId);
  if (item) {
    item.threshold = val;
    triggerCropPreview();
  }
});

elements.rangePadding.addEventListener('input', (e) => {
  const val = parseInt(e.target.value);
  elements.valPadding.textContent = `${val}px`;
  const item = state.items.find((i) => i.id === state.selectedItemId);
  if (item) {
    item.padding = val;
    triggerCropPreview();
  }
});

elements.btnApplyAllThreshold.addEventListener('click', () => {
  const currentThresh = parseInt(elements.rangeThreshold.value);
  const currentPad = parseInt(elements.rangePadding.value);
  state.items.forEach((item) => {
    item.threshold = currentThresh;
    item.padding = currentPad;
  });
  showToast(`تنظیمات (آستانه: ${currentThresh}، حاشیه: ${currentPad}px) برای تمام ${state.items.length} امضا اعمال شد`, 'success');
});

// Tab Switch
elements.previewTabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    elements.previewTabs.forEach((t) => t.classList.remove('active'));
    tab.classList.add('active');
    const tabName = tab.dataset.tab;
    state.activeTab = tabName;
    elements.imgTransPreview.style.display = tabName === 'trans' ? 'block' : 'none';
    elements.imgRawPreview.style.display = tabName === 'raw' ? 'block' : 'none';
  });
});

// Delete Selected Box
function deleteSelectedItem() {
  if (!state.selectedItemId) return;
  state.items = state.items.filter((i) => i.id !== state.selectedItemId);
  showToast('کادر حذف شد', 'info');
  if (state.items.length > 0) {
    selectItem(state.items[0].id);
  } else {
    state.selectedItemId = null;
    clearPreview();
    renderOverlay();
    renderItemsList();
  }
}

elements.btnDeleteBox.addEventListener('click', deleteSelectedItem);

// Keyboard Shortcuts (Delete / Backspace for removing selected box)
window.addEventListener('keydown', (e) => {
  if (e.key === 'Delete' || e.key === 'Backspace') {
    // Do not trigger deletion if the user is typing in an input field or textarea
    const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
    if (activeTag === 'input' || activeTag === 'textarea' || document.activeElement?.isContentEditable) {
      return;
    }
    
    if (state.activeModule === 'extractor' && state.selectedItemId) {
      e.preventDefault();
      deleteSelectedItem();
    }
  }
});

// Save Single
elements.btnSaveSingle.addEventListener('click', async () => {
  const item = state.items.find((i) => i.id === state.selectedItemId);
  if (!item || !state.selectedScan) return;

  try {
    const res = await fetch('/api/save-signatures', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: state.selectedScan,
        items: [item]
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`امضای ${item.empCode} با موفقیت در output/signatures ذخیره شد!`, 'success');
    } else {
      showToast(data.error || 'خطا در ذخیره امضا', 'error');
    }
  } catch (err) {
    showToast('خطا در ارتباط با سرور', 'error');
  }
});

// Save All
elements.btnSaveAll.addEventListener('click', async () => {
  if (state.items.length === 0 || !state.selectedScan) {
    showToast('هیچ امضایی برای ذخیره وجود ندارد', 'error');
    return;
  }

  showToast('در حال ذخیره و پردازش تمام امضاها...', 'info');
  try {
    const res = await fetch('/api/save-signatures', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: state.selectedScan,
        items: state.items
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`🎉 تعداد ${data.savedCount} فایل PNG شفاف در مسیر خروجی ذخیره شد!`, 'success');
    } else {
      showToast(data.error || 'خطا در ذخیره فایل‌ها', 'error');
    }
  } catch (err) {
    showToast('خطا در ذخیره', 'error');
  }
});

// Initial Startup
fetchScans();
fetchEmployeesData();
