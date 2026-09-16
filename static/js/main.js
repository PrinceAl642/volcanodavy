/* static/js/main.js */
/* Logic Utama Application Frontend Volcano Monitoring Center */

const INDONESIAN_DAYS = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
const INDONESIAN_MONTHS = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni",
  "Juli", "Agustus", "September", "Oktober", "November", "Desember"
];

document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initSidebar();
  initThemeToggle();
  initSopWidgetLocalStorage();

  loadDashboardData();
  loadKubahLavaData();
  loadPanduanData();
  loadAlertsData();
  loadCuacaWidget();

  // Auto Refresh Polling 10 detik
  setInterval(() => {
    loadDashboardData();
    loadCuacaWidget();
  }, 10000);

  initEventStream();
});

/* Realtime Clock - WIB */
function initClock() {
  const clockEl = document.getElementById('realtime-clock-wib');
  if (!clockEl) return;

  function updateClock() {
    const now = new Date();
    const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
    const wibDate = new Date(utc + (3600000 * 7));

    const day = INDONESIAN_DAYS[wibDate.getDay()];
    const date = wibDate.getDate();
    const month = INDONESIAN_MONTHS[wibDate.getMonth()];
    const year = wibDate.getFullYear();

    const hours = String(wibDate.getHours()).padStart(2, '0');
    const minutes = String(wibDate.getMinutes()).padStart(2, '0');
    const seconds = String(wibDate.getSeconds()).padStart(2, '0');

    clockEl.innerText = `${day}, ${date} ${month} ${year} ${hours}:${minutes}:${seconds} WIB`;
  }

  updateClock();
  setInterval(updateClock, 1000);
}

/* Navigation & Sidebar */
function initSidebar() {
  const menuButtons = document.querySelectorAll('.sidebar-menu button[data-section]');
  const sections = document.querySelectorAll('.content-section');

  menuButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      menuButtons.forEach(b => b.classList.remove('active'));
      sections.forEach(s => s.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.getAttribute('data-section');
      const targetSection = document.getElementById(targetId);
      if (targetSection) {
        targetSection.classList.add('active');
        if (targetId === 'sec-peta-gempa') {
          setTimeout(initEarthquakeMap, 100);
        }
      }
    });
  });
}

function openSection(sectionId) {
  const btn = document.querySelector(`.sidebar-menu button[data-section="${sectionId}"]`);
  if (btn) btn.click();
}

/* Theme Toggle */
function initThemeToggle() {
  const btnToggle = document.getElementById('btn-theme-toggle');
  if (!btnToggle) return;

  btnToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    btnToggle.innerHTML = newTheme === 'dark' ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
  });
}

/* SOP Widget LocalStorage */
function initSopWidgetLocalStorage() {
  const btnRead = document.getElementById('btn-sop-read-confirm');
  if (!btnRead) return;

  const isRead = localStorage.getItem('sop_pendakian_read') === 'true';
  if (isRead) {
    btnRead.classList.remove('btn-outline-success');
    btnRead.classList.add('btn-success');
    btnRead.innerHTML = '<i class="bi bi-check-circle-fill"></i> [ ✔ ] Saya Sudah Membaca SOP';
  }

  btnRead.addEventListener('click', () => {
    const currentState = localStorage.getItem('sop_pendakian_read') === 'true';
    if (!currentState) {
      localStorage.setItem('sop_pendakian_read', 'true');
      btnRead.classList.remove('btn-outline-success');
      btnRead.classList.add('btn-success');
      btnRead.innerHTML = '<i class="bi bi-check-circle-fill"></i> [ ✔ ] Saya Sudah Membaca SOP';
    } else {
      localStorage.setItem('sop_pendakian_read', 'false');
      btnRead.classList.remove('btn-success');
      btnRead.classList.add('btn-outline-success');
      btnRead.innerHTML = '<i class="bi bi-check-lg"></i> [ ✔ ] Saya Sudah Membaca SOP';
    }
  });
}

/* Load Dashboard Data */
function loadDashboardData() {
  fetch('/api/statistik')
    .then(res => res.json())
    .then(data => {
      const counts = data.status_counts || {};
      document.getElementById('stat-normal-count').innerText = counts['Normal'] || 0;
      document.getElementById('stat-waspada-count').innerText = counts['Waspada'] || 0;
      document.getElementById('stat-siaga-count').innerText = counts['Siaga'] || 0;
      document.getElementById('stat-awas-count').innerText = counts['Awas'] || 0;
      document.getElementById('stat-gempa-today').innerText = data.total_gempa_today || 0;

      const mostActive = data.most_active_volcano || {};
      document.getElementById('stat-most-active').innerText = mostActive.gunung || '-';

      renderStatusChart(counts);
      if (data.grafik_7_hari) renderActivity7dChart(data.grafik_7_hari);
      if (data.grafik_30_hari) renderActivity30dChart(data.grafik_30_hari);
    })
    .catch(err => console.error("Error loading dashboard stats:", err));

  // Volcano Cards
  fetch('/api/status')
    .then(res => res.json())
    .then(data => {
      const container = document.getElementById('volcano-cards-container');
      if (!container) return;

      const gunung = data.gunung || {};
      let html = '';

      for (const [slug, status] of Object.entries(gunung)) {
        if (!status) continue;
        const meta = status.meta || {};
        const levelCode = status.level || 'I';
        const levelLabel = status.level_label || 'Status Aktivitas Tidak Tersedia';
        const color = status.color || '#4C9A7E';
        const ringkasan = status.ringkasan || 'Data sementara tidak tersedia.';
        const fetchedAt = status.fetched_at ? new Date(status.fetched_at).toLocaleString('id-ID') + ' WIB' : 'Data sementara tidak tersedia';

        html += `
          <div class="panel-card" style="border-left: 4px solid ${color};">
            <div class="panel-header mb-2">
              <div>
                <div class="panel-title text-capitalize">🌋 Gunung ${meta.nama || slug}</div>
                <div style="font-size:12px; color:var(--text-muted);">${meta.lokasi || 'Indonesia'} (${meta.ketinggian || '-'} mdpl)</div>
              </div>
              <span class="badge-level" style="background:${color}; color:#fff;">Level ${levelCode} - ${levelLabel}</span>
            </div>
            <p style="font-size:13.5px; line-height:1.5; color:var(--text-main); margin-bottom:12px;">${ringkasan}</p>
            <div class="d-flex justify-content-between align-items-center">
              <small style="font-size:11px; color:var(--text-muted);">Update Terakhir: ${fetchedAt}</small>
              <button type="button" class="btn btn-sm btn-outline-warning fw-bold" onclick="viewCctvModal('${slug}')"><i class="bi bi-camera-video-fill"></i> CCTV</button>
            </div>
          </div>
        `;
      }
      container.innerHTML = html;
    })
    .catch(err => console.error("Error loading volcano cards:", err));
}

/* Modal CCTV Preview & Fallback Handling */
function viewCctvModal(slug) {
  const modalEl = document.getElementById('modalCctvPreview');
  const titleEl = document.getElementById('modalCctvGunungTitle');
  const bodyEl = document.getElementById('modalCctvBody');

  if (!modalEl || !bodyEl) {
    console.error("Elemen modal CCTV tidak ditemukan.");
    return;
  }

  if (titleEl) titleEl.innerText = `Pratinjau CCTV Real-Time — GUNUNG ${slug.toUpperCase()}`;

  bodyEl.innerHTML = `
    <div class="text-center py-4 text-muted">
      <div class="spinner-border text-warning mb-2" role="status"></div>
      <div>Menghubungkan ke aliran kamera CCTV MAGMA ESDM...</div>
    </div>
  `;

  // Display Modal via Bootstrap API or Fallback
  try {
    if (window.bootstrap && window.bootstrap.Modal) {
      const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
      bsModal.show();
    } else {
      modalEl.style.display = 'block';
      modalEl.classList.add('show');
    }
  } catch (e) {
    modalEl.style.display = 'block';
    modalEl.classList.add('show');
  }

  fetch(`/api/cctv/${slug}`)
    .then(res => res.json())
    .then(data => {
      if (data.tersedia && data.kamera && data.kamera.length > 0) {
        let galleryHtml = '<div class="row g-3">';
        data.kamera.forEach(cam => {
          const imgUrl = cam.snapshot_url || cam.source_url;
          const camTime = cam.fetched_at ? new Date(cam.fetched_at).toLocaleString('id-ID') + ' WIB' : '-';

          galleryHtml += `
            <div class="col-md-6">
              <div class="card bg-dark text-light border-secondary">
                <img src="${imgUrl}" class="card-img-top" alt="${cam.camera_name}" style="height: 220px; object-fit: cover;" onerror="this.onerror=null; this.src='https://via.placeholder.com/400x220?text=CCTV+Tidak+Dapat+Diakses';">
                <div class="card-body p-2 text-center">
                  <h6 class="card-title m-0 text-warning" style="font-size:13px;">${cam.camera_name}</h6>
                  <small class="text-muted" style="font-size:11px;">Update: ${camTime}</small>
                </div>
              </div>
            </div>
          `;
        });
        galleryHtml += '</div>';
        bodyEl.innerHTML = galleryHtml;
      } else {
        bodyEl.innerHTML = `
          <div class="alert alert-warning text-center my-3 p-4 border-warning">
            <i class="bi bi-camera-video-off fs-1 d-block mb-2 text-warning"></i>
            <h5 class="fw-bold text-warning">CCTV tidak ada atau tidak bisa diakses</h5>
            <p class="m-0 small text-muted">Kamera CCTV untuk gunung ini belum tersedia atau sedang tidak dapat diakses dari sumber MAGMA Indonesia.</p>
          </div>
        `;
      }
    })
    .catch(err => {
      bodyEl.innerHTML = `
        <div class="alert alert-danger text-center my-3 p-4 border-danger">
          <i class="bi bi-exclamation-octagon fs-1 d-block mb-2 text-danger"></i>
          <h5 class="fw-bold text-light">CCTV tidak ada atau tidak bisa diakses</h5>
          <p class="m-0 small text-muted">Gagal menghubungkan aliran kamera CCTV.</p>
        </div>
      `;
    });
}

function closeCctvModal() {
  const modalEl = document.getElementById('modalCctvPreview');
  if (!modalEl) return;
  try {
    if (window.bootstrap && window.bootstrap.Modal) {
      const bsModal = bootstrap.Modal.getInstance(modalEl);
      if (bsModal) bsModal.hide();
    }
  } catch (e) {}
  modalEl.style.display = 'none';
  modalEl.classList.remove('show');
}

/* Load Weather Widget (Open Meteo) */
function loadCuacaWidget() {
  fetch('/api/cuaca')
    .then(res => res.json())
    .then(data => {
      const container = document.getElementById('weather-widget-container');
      if (!container) return;

      const cuaca = data.cuaca || {};
      let html = '';

      for (const [slug, w] of Object.entries(cuaca)) {
        if (!w || !w.suhu_c) continue;
        html += `
          <div class="sop-box" style="padding:10px 14px;">
            <div style="font-weight:bold; font-size:13px; color:var(--accent-blue); text-transform:capitalize;">🌋 Gunung ${slug}</div>
            <div style="font-size:18px; font-weight:bold; margin-top:2px;">${w.suhu_c}°C</div>
            <div style="font-size:11px; color:var(--text-muted);">${w.kondisi || '-'} | Angin ${w.kecepatan_angin_kmh || 0} km/h</div>
          </div>
        `;
      }
      container.innerHTML = html || '<div class="text-muted small">Data sementara tidak tersedia.</div>';
    })
    .catch(err => console.error("Error loading cuaca:", err));
}

/* Load Kubah Lava Data */
function loadKubahLavaData() {
  fetch('/api/kubah-lava')
    .then(res => res.json())
    .then(data => {
      const tbody = document.getElementById('table-kubah-lava-body');
      if (!tbody) return;

      const items = data.kubah_lava || [];
      let html = '';

      items.forEach(item => {
        const volumeStr = item.volume_kubah_m3 ? `${item.volume_kubah_m3.toLocaleString('id-ID')} m³` : 'Data sementara tidak tersedia.';
        const tinggiStr = item.tinggi_kubah_m ? `${item.tinggi_kubah_m} m` : 'Data sementara tidak tersedia.';
        const deltaStr = item.pertumbuhan_kubah_m3 ? `${item.pertumbuhan_kubah_m3 > 0 ? '+' : ''}${item.pertumbuhan_kubah_m3.toLocaleString('id-ID')} m³` : '-';
        const updateStr = item.waktu_update_terakhir ? new Date(item.waktu_update_terakhir).toLocaleString('id-ID') : 'Data sementara tidak tersedia.';

        html += `
          <tr>
            <td><strong>${item.nama_gunung}</strong></td>
            <td><span class="badge-level" style="background:${item.color}; color:#fff;">Level ${item.level_code} - ${item.status_aktivitas}</span></td>
            <td>${tinggiStr}</td>
            <td>${volumeStr}</td>
            <td>${deltaStr}</td>
            <td>${item.status_morfologi}</td>
            <td>${updateStr}</td>
            <td><button class="btn btn-sm btn-outline-warning" onclick="selectKubahLavaChart('${item.slug}', '${item.nama_gunung}')">Grafik</button></td>
          </tr>
        `;
      });

      tbody.innerHTML = html || '<tr><td colspan="8" class="text-center text-muted">Data sementara tidak tersedia.</td></tr>';

      if (items.length > 0) {
        selectKubahLavaChart(items[0].slug, items[0].nama_gunung);
      }
    })
    .catch(err => console.error("Error loading kubah lava:", err));
}

function selectKubahLavaChart(slug, gunungName) {
  fetch(`/api/kubah-lava/${slug}`)
    .then(res => res.json())
    .then(data => {
      if (data.chart_series) {
        renderKubahLavaChart(data.chart_series, gunungName);
      }
    })
    .catch(err => console.error("Error loading kubah lava series:", err));
}

/* Load Panduan Pendakian */
function loadPanduanData() {
  fetch('/api/panduan')
    .then(res => res.json())
    .then(data => {
      renderChecklistItems(data.checklist_peralatan ? data.checklist_peralatan.items : [], 'sop-dashboard-checklist-container');
      renderChecklistItems(data.checklist_peralatan ? data.checklist_peralatan.items : [], 'panduan-checklist-container');

      const elSyarat = document.getElementById('panduan-syarat-content');
      if (elSyarat && data.syarat_mendaki) {
        let html = '<ul style="list-style:none; padding:0; display:grid; gap:10px;">';
        data.syarat_mendaki.items.forEach(it => {
          html += `
            <li style="padding:12px; background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-md);">
              <strong style="color:var(--accent-orange);">• ${it.nama}</strong>
              <p style="margin-top:4px; font-size:13px;">${it.detail}</p>
            </li>
          `;
        });
        html += '</ul>';
        elSyarat.innerHTML = html;
      }
    })
    .catch(err => console.error("Error loading panduan data:", err));
}

function renderChecklistItems(items, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;

  let html = '';
  items.forEach(it => {
    const checkedAttr = it.checked ? 'checked' : '';
    const checkedClass = it.checked ? 'checked' : '';

    html += `
      <label class="checklist-item ${checkedClass}" id="lbl-${containerId}-${it.key}">
        <input type="checkbox" ${checkedAttr} onchange="toggleChecklistItem('${it.key}', this.checked)">
        <span>${it.label}</span>
      </label>
    `;
  });
  el.innerHTML = html;
}

function toggleChecklistItem(key, isChecked) {
  fetch('/api/panduan/checklist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key: key, checked: isChecked })
  })
  .then(() => loadPanduanData())
  .catch(err => console.error("Error updating checklist:", err));
}

/* Load Alerts Log */
function loadAlertsData() {
  fetch('/api/peringatan')
    .then(res => res.json())
    .then(data => {
      const container = document.getElementById('activity-feed-container');
      if (!container) return;

      const alerts = data.data || [];
      let html = '';

      alerts.forEach(a => {
        const timeStr = a.terkirim_at ? new Date(a.terkirim_at).toLocaleString('id-ID') + ' WIB' : '-';
        html += `
          <div class="feed-item">
            <div class="feed-time">${timeStr} | Channel: ${a.channel} (${a.status_kirim})</div>
            <div style="margin-top:4px; white-space:pre-wrap; font-family:'IBM Plex Mono',monospace;">${a.pesan}</div>
          </div>
        `;
      });

      container.innerHTML = html || '<div class="text-muted small">Belum ada riwayat notifikasi.</div>';
    })
    .catch(err => console.error("Error loading alerts:", err));
}

function sendTelegramTest() {
  const btn = document.getElementById('btn-test-telegram');
  if (btn) btn.disabled = true;

  fetch('/api/peringatan/test', { method: 'POST' })
    .then(res => res.json())
    .then(res => {
      alert(`Status Pengiriman Instant Telegram: ${res.message}`);
      loadAlertsData();
    })
    .catch(err => alert("Gagal tes telegram: " + err))
    .finally(() => { if (btn) btn.disabled = false; });
}

function sendTelegramHourlyTest() {
  fetch('/api/peringatan/hourly-test', { method: 'POST' })
    .then(res => res.json())
    .then(res => {
      alert(`Status Pengiriman Laporan 1 Jam Telegram: ${res.message}`);
      loadAlertsData();
    })
    .catch(err => alert("Gagal tes laporan 1 jam: " + err));
}

/* SSE Stream */
function initEventStream() {
  if (!window.EventSource) return;
  const source = new EventSource('/api/stream');
  source.onmessage = function (e) {
    if (e.data && !e.data.startsWith(':')) {
      try {
        const payload = JSON.parse(e.data);
        if (payload.gunung) loadDashboardData();
      } catch (err) {}
    }
  };
}
