// ========== Configuración global optimizada ==========
(() => {
  if (typeof Chart !== 'undefined') {
    Chart.defaults.color = '#cfe0ff';
    Chart.defaults.borderColor = 'rgba(255,255,255,.1)';
    Chart.defaults.font.family = 'system-ui, -apple-system, sans-serif';
    Chart.defaults.animation = false; // Desactivar todas las animaciones
  }
})();

// ========== Sparklines sin animación ==========
(() => {
  if (typeof Chart === 'undefined') return;
  
  const createSparkline = (id, data, color) => {
    const el = document.getElementById(id);
    if (!el) return;
    
    new Chart(el, {
      type: 'line',
      data: {
        datasets: [{
          data: data,
          borderColor: color,
          backgroundColor: 'transparent',
          pointRadius: 0,
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        scales: {
          x: { display: false },
          y: { display: false }
        }
      }
    });
  };
  
  createSparkline('sparkAlumnos', [30, 35, 42], '#8ab4ff');
  createSparkline('sparkRutinas', [96, 110, 115], '#7ae1c3');
  createSparkline('sparkPersonal', [9, 12, 15], '#ffd166');
})();

// ========== Gráficos principales sin animación ==========
(() => {
  if (typeof Chart === 'undefined') return;
  
  // Gráfico de Asistencia
  const ctxA = document.getElementById('chartAsistencia');
  if (ctxA) {
    new Chart(ctxA, {
      type: 'line',
      data: {
        labels: ['S1', 'S2', 'S3', 'S4'],
        datasets: [{
          data: [4, 5, 6, 5],
          borderColor: '#8ab4ff',
          backgroundColor: 'rgba(138, 180, 255, 0.1)',
          pointBackgroundColor: '#8ab4ff',
          pointRadius: 3,
          borderWidth: 2,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            ticks: { color: '#cfe0ff' },
            grid: { display: false }
          },
          y: {
            beginAtZero: true,
            ticks: { 
              color: '#cfe0ff',
              stepSize: 1
            },
            grid: { color: 'rgba(255,255,255,.05)' }
          }
        }
      }
    });
  }
  
  // Gráfico de Progreso
  const ctxP = document.getElementById('chartProgreso');
  if (ctxP) {
    new Chart(ctxP, {
      type: 'doughnut',
      data: {
        labels: ['Completadas', 'Pendientes'],
        datasets: [{
          data: [32, 13],
          backgroundColor: ['#7ae1c3', '#ffd166'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        cutout: '65%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#cfe0ff',
              padding: 15,
              usePointStyle: true
            }
          }
        }
      }
    });
  }
})();