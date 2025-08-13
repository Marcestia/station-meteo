document.addEventListener("DOMContentLoaded", () => {
  // ==========================
  // 1. Carte Leaflet avec tous les points et zoom automatique
  // ==========================
  if (typeof locationsData !== 'undefined') {
    const map = L.map('map').setView([44.8, -1.0], 7);

    // Couche OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap'
    }).addTo(map);

    // Icônes personnalisées
    const defaultIcon = L.icon({
      iconUrl: '/static/images/marker-blue.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41]
    });

    const activeIcon = L.icon({
      iconUrl: '/static/images/marker-red.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41]
    });

    const bounds = [];

    // Ajouter les marqueurs
    Object.entries(locationsData).forEach(([name, position]) => {
      const marker = L.marker([position.lat, position.lon], {
        icon: (typeof selectedLocation !== 'undefined' && name === selectedLocation)
          ? activeIcon
          : defaultIcon
      }).addTo(map);

      // Tooltip au survol
      marker.bindTooltip(name.charAt(0).toUpperCase() + name.slice(1), {
        permanent: false,
        direction: 'top'
      });

      // Clic → redirection (seulement location)
      marker.on('click', () => {
        window.location.href = `/?location=${name}`;
      });

      bounds.push([position.lat, position.lon]);
    });

    // Ajuste la vue pour afficher tous les points
    if (bounds.length > 0) {
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }

  // ==========================
  // 2. Bouton Refresh
  // ==========================
  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => location.reload());
  }

  // ==========================
  // 3. Dark Mode Toggle
  // ==========================
  const darkToggle = document.getElementById('darkModeToggle');
  const body = document.body;

  // Charger la préférence depuis localStorage
  if (localStorage.getItem('theme') === 'dark') {
    body.classList.add('dark-mode');
    darkToggle.textContent = '☀️ Mode clair';
  }

  // Toggle du mode
  if (darkToggle) {
    darkToggle.addEventListener('click', () => {
      body.classList.toggle('dark-mode');
      if (body.classList.contains('dark-mode')) {
        localStorage.setItem('theme', 'dark');
        darkToggle.textContent = '☀️ Mode clair';
      } else {
        localStorage.setItem('theme', 'light');
        darkToggle.textContent = '🌙 Mode sombre';
      }
    });
  }

  // ==========================
  // 4. Gestion des sections (checkboxes)
  // ==========================
  const sections = {
    weather: [document.getElementById('section-weather'), document.getElementById('section-weather-extra')],
    wind: [document.getElementById('section-wind')],
    surf: [document.getElementById('section-surf')],
    webcams: [document.getElementById('section-webcams')],
    generalWeather: [document.getElementById('section-general-weather')],
    openmeteoWeather: [document.getElementById('section-openmeteo-weather')] // ✅ Ajout Open-Meteo
    };

    const toggles = {
        weather: document.getElementById('toggle-weather'),
        wind: document.getElementById('toggle-wind'),
        surf: document.getElementById('toggle-surf'),
        webcams: document.getElementById('toggle-webcams'),
        generalWeather: document.getElementById('toggle-general-weather'),
        openmeteoWeather: document.getElementById('toggle-openmeteo-weather') // ✅ Ajout Open-Meteo
    };


  for (const key in toggles) {
    const saved = localStorage.getItem(`show_${key}`);
    toggles[key].checked = saved === 'true';
    sections[key].forEach(sec => {
      if (sec) sec.classList.toggle('visible', toggles[key].checked);
    });

    toggles[key].addEventListener('change', () => {
      localStorage.setItem(`show_${key}`, toggles[key].checked);
      sections[key].forEach(sec => {
        if (sec) sec.classList.toggle('visible', toggles[key].checked);
      });
    });
  }

  // ==========================
  // 5. Gestion du changement de lieu
  // ==========================
  const locationSelect = document.getElementById('location');
  if (locationSelect) {
    locationSelect.addEventListener('change', () => {
      window.location.href = `/?location=${locationSelect.value}`;
    });
  }

  // ==========================
  // 6. Modal Webcams (plein écran)
  // ==========================
  const modal = document.getElementById('webcam-modal');
  const modalIframe = document.getElementById('modal-iframe');
  const closeBtn = document.querySelector('.modal-close');

  document.querySelectorAll('.webcam-fullscreen').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const iframeURL = e.target.closest('.webcam-card').getAttribute('data-iframe');
      modalIframe.src = iframeURL;
      modal.style.display = 'flex';
    });
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      modal.style.display = 'none';
      modalIframe.src = ''; // Stop la webcam
    });
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.style.display = 'none';
        modalIframe.src = '';
      }
    });
  }
});


// ==========================
// 7. Vent mobile : toggle entre carte courante et scroll complet
// ==========================
(function () {
  const isMobile = window.matchMedia('(max-width: 768px)').matches;
  if (!isMobile) return;

  function parseFRDate(ddmmyyyy) {
    const [dd, mm, yyyy] = ddmmyyyy.split('/').map(Number);
    return new Date(yyyy, mm - 1, dd);
  }
  function parseTime(hms) {
    const parts = hms.split(':').map(Number);
    return { h: parts[0] || 0, m: parts[1] || 0 };
  }

  document.querySelectorAll('#section-wind .wind-grid').forEach(grid => {
    const dayTitles = grid.querySelectorAll('.wind-day');
    const rows = grid.querySelectorAll('.wind-cards');

    dayTitles.forEach((titleEl, idx) => {
      const row = rows[idx];
      if (!row) return;

      // trouver la carte la plus proche de l'heure actuelle
      const day = parseFRDate(titleEl.textContent.trim());
      const now = new Date();
      let bestCard = null, bestDiff = Infinity;

      row.querySelectorAll('.wind-card').forEach(card => {
        const t = card.querySelector('.wind-time')?.textContent.trim().slice(0, 5);
        if (!t) return;
        const { h, m } = parseTime(t);
        const dt = new Date(day.getFullYear(), day.getMonth(), day.getDate(), h, m);
        const diff = Math.abs(dt - now);
        if (diff < bestDiff) { bestDiff = diff; bestCard = card; }
      });

      if (bestCard) {
        bestCard.classList.add('is-current');
        row.classList.add('collapsed');

        // gestion du toggle
        row.addEventListener('click', (e) => {
          if (row.classList.contains('collapsed')) {
            // passer en mode scroll
            row.classList.remove('collapsed');
            setTimeout(() => {
              bestCard.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
            }, 0);
          } else {
            // revenir au mode 1 carte
            row.classList.add('collapsed');
          }
        });
      }
    });
  });
})();
