/* static/js/map.js */
/* Interactive Leaflet Map for Volcanoes & BMKG/USGS Earthquakes */

let mapInstance = null;
let volcanoLayerGroup = null;
let earthquakeLayerGroup = null;

function initEarthquakeMap() {
  const mapContainer = document.getElementById('leaflet-map');
  if (!mapContainer) return;

  if (mapInstance) {
    mapInstance.invalidateSize();
    return;
  }

  // Centered on Indonesia
  mapInstance = L.map('leaflet-map', {
    center: [-2.5489, 118.0149],
    zoom: 5,
    minZoom: 4,
    maxZoom: 12
  });

  // Dark Mode Tile Layer
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(mapInstance);

  volcanoLayerGroup = L.layerGroup().addTo(mapInstance);
  earthquakeLayerGroup = L.layerGroup().addTo(mapInstance);

  loadMapData();
}

function loadMapData() {
  if (!mapInstance) return;

  // Load Volcanoes
  fetch('/api/status')
    .then(res => res.json())
    .then(data => {
      if (!volcanoLayerGroup) return;
      volcanoLayerGroup.clearLayers();

      const gunung = data.gunung || {};
      for (const [slug, status] of Object.entries(gunung)) {
        if (!status) continue;
        const meta = status.meta || {};
        const lat = meta.lat;
        const lon = meta.lon;

        if (!lat || !lon) continue;

        const color = status.color || '#8b9bb4';
        const levelCode = status.level || 'I';
        const levelLabel = status.level_label || 'Status Aktivitas Tidak Tersedia';
        const ringkasan = status.ringkasan || 'Data sementara tidak tersedia.';
        const fetchedAt = status.fetched_at ? new Date(status.fetched_at).toLocaleString('id-ID') + ' WIB' : 'Data sementara tidak tersedia';

        // Colored circle marker
        const marker = L.circleMarker([lat, lon], {
          radius: 8,
          fillColor: color,
          color: '#ffffff',
          weight: 1.5,
          opacity: 1,
          fillOpacity: 0.9
        });

        const popupContent = `
          <div style="font-family: 'Outfit', sans-serif; color: #111; min-width: 220px;">
            <h6 style="margin: 0 0 4px 0; font-weight: bold; color: #161b26;">🌋 Gunung ${meta.nama || slug}</h6>
            <div style="font-size: 11px; color: #555; margin-bottom: 6px;">📍 ${meta.lokasi || 'Indonesia'} | 🏔 ${meta.ketinggian || '-'} mdpl</div>
            <div style="margin-bottom: 6px;"><span class="badge" style="background:${color}; color:#fff; font-size:11px;">Level ${levelCode} - ${levelLabel}</span></div>
            <p style="font-size: 12px; line-height: 1.4; margin-bottom: 6px;">${ringkasan}</p>
            <div style="font-size: 10px; color: #777;">Lat: ${lat}, Lon: ${lon}</div>
            <div style="font-size: 10px; color: #777; margin-bottom: 8px;">Update: ${fetchedAt}</div>
            <button class="btn btn-sm btn-warning text-dark fw-bold w-100" onclick="viewCctvModal('${slug}')">
              <i class="bi bi-camera-video-fill"></i> Lihat CCTV
            </button>
          </div>
        `;

        marker.bindPopup(popupContent);
        volcanoLayerGroup.addLayer(marker);
      }
    })
    .catch(err => console.error("Error loading map volcanoes:", err));

  // Load Earthquakes (BMKG & USGS)
  fetch('/api/gempa-realtime')
    .then(res => res.json())
    .then(data => {
      if (!earthquakeLayerGroup) return;
      earthquakeLayerGroup.clearLayers();

      const quakes = data.gempa || [];
      quakes.forEach(q => {
        const lat = q.lat;
        const lon = q.lon;
        if (!lat || !lon) return;

        const mag = parseFloat(q.magnitudo) || 3.0;
        const radius = Math.max(5, mag * 2.5);

        const marker = L.circleMarker([lat, lon], {
          radius: radius,
          fillColor: '#00b4d8',
          color: '#ffffff',
          weight: 1,
          opacity: 0.9,
          fillOpacity: 0.6
        });

        const popupContent = `
          <div style="font-family: 'Outfit', sans-serif; color: #111;">
            <h6 style="margin: 0 0 4px 0; font-weight: bold; color: #0077b6;">🌍 Gempa Terkini (${q.sumber || 'BMKG'})</h6>
            <div style="font-size: 13px; font-weight: bold; color: #d90429;">Magnitudo: M ${q.magnitudo || '-'}</div>
            <div style="font-size: 11.5px; margin-bottom: 4px;">Kedalaman: ${q.kedalaman || '-'}</div>
            <div style="font-size: 11.5px; margin-bottom: 4px;">Lokasi: ${q.lokasi || '-'}</div>
            <div style="font-size: 10px; color: #666;">Waktu: ${q.tanggal || ''} ${q.jam || ''} WIB</div>
          </div>
        `;

        marker.bindPopup(popupContent);
        earthquakeLayerGroup.addLayer(marker);
      });

      const syncEl = document.getElementById('map-last-sync');
      if (syncEl) syncEl.innerText = `Terhubung: ${quakes.length} Gempa & 44+ Gunung (BMKG/MAGMA)`;
    })
    .catch(err => console.error("Error loading map earthquakes:", err));
}
