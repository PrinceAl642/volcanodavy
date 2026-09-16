/* static/js/charts.js */
/* Interactive Charts using Chart.js */

let statusDoughnutChart = null;
let activity7dChart = null;
let activity30dChart = null;
let kubahLavaChart = null;

function renderStatusChart(counts) {
  const ctx = document.getElementById('chart-status-breakdown');
  if (!ctx) return;

  const dataValues = [
    counts['Normal'] || 0,
    counts['Waspada'] || 0,
    counts['Siaga'] || 0,
    counts['Awas'] || 0
  ];

  if (statusDoughnutChart) {
    statusDoughnutChart.data.datasets[0].data = dataValues;
    statusDoughnutChart.update();
    return;
  }

  statusDoughnutChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Normal', 'Waspada', 'Siaga', 'Awas'],
      datasets: [{
        data: dataValues,
        backgroundColor: ['#4C9A7E', '#E8B923', '#E8730C', '#C1272D'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#8b9bb4', font: { family: 'Outfit' } }
        }
      }
    }
  });
}

function renderActivity7dChart(series) {
  const ctx = document.getElementById('chart-activity-7d');
  if (!ctx) return;

  const labels = series.map(s => s.tanggal);
  const dataValues = series.map(s => s.jumlah);

  if (activity7dChart) {
    activity7dChart.data.labels = labels;
    activity7dChart.data.datasets[0].data = dataValues;
    activity7dChart.update();
    return;
  }

  activity7dChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Jumlah Kejadian Gempa',
        data: dataValues,
        backgroundColor: '#ff6b35',
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: '#8b9bb4' }, grid: { display: false } },
        y: { ticks: { color: '#8b9bb4' }, grid: { color: 'rgba(255,255,255,0.05)' } }
      },
      plugins: {
        legend: { labels: { color: '#8b9bb4' } }
      }
    }
  });
}

function renderActivity30dChart(series) {
  const ctx = document.getElementById('chart-activity-30d');
  if (!ctx) return;

  const labels = series.map(s => s.tanggal);
  const dataValues = series.map(s => s.jumlah);

  if (activity30dChart) {
    activity30dChart.data.labels = labels;
    activity30dChart.data.datasets[0].data = dataValues;
    activity30dChart.update();
    return;
  }

  activity30dChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Aktivitas 30 Hari (Kejadian)',
        data: dataValues,
        borderColor: '#00b4d8',
        backgroundColor: 'rgba(0, 180, 216, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: '#8b9bb4' }, grid: { display: false } },
        y: { ticks: { color: '#8b9bb4' }, grid: { color: 'rgba(255,255,255,0.05)' } }
      },
      plugins: {
        legend: { labels: { color: '#8b9bb4' } }
      }
    }
  });
}

function renderKubahLavaChart(series, gunungName) {
  const ctx = document.getElementById('chart-kubah-lava-series');
  if (!ctx) return;

  const labels = series.map(s => s.tanggal);
  const volumes = series.map(s => s.volume_m3 || 0);

  if (kubahLavaChart) {
    kubahLavaChart.data.labels = labels;
    kubahLavaChart.data.datasets[0].label = `Volume Kubah Lava (${gunungName})`;
    kubahLavaChart.data.datasets[0].data = volumes;
    kubahLavaChart.update();
    return;
  }

  kubahLavaChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: `Volume Kubah Lava (${gunungName})`,
        data: volumes,
        borderColor: '#e8730c',
        backgroundColor: 'rgba(232, 115, 12, 0.15)',
        fill: true,
        tension: 0.3,
        pointRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: '#8b9bb4' }, grid: { display: false } },
        y: { ticks: { color: '#8b9bb4' }, grid: { color: 'rgba(255,255,255,0.05)' } }
      },
      plugins: {
        legend: { labels: { color: '#8b9bb4' } }
      }
    }
  });
}
