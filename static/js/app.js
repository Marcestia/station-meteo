document.addEventListener('DOMContentLoaded', () => {
  const locationSelect = document.getElementById('location');
  if (locationSelect) {
    locationSelect.addEventListener('change', () => {
      window.location.href = `/?location=${locationSelect.value}`;
    });
  }

  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) refreshBtn.addEventListener('click', () => window.location.reload());

  if (typeof locationsData !== 'undefined') {
    const map = L.map('map').setView([44.8, -1.0], 7);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' }).addTo(map);
    const bounds = [];
    Object.entries(locationsData).forEach(([name, position]) => {
      const marker = L.marker([position.lat, position.lon]).addTo(map);
      marker.bindPopup(name.charAt(0).toUpperCase() + name.slice(1));
      marker.on('click', () => window.location.href = `/?location=${name}`);
      bounds.push([position.lat, position.lon]);
    });
    if (bounds.length) map.fitBounds(bounds, { padding: [40, 40] });
  }

  const modal = document.getElementById('webcam-modal');
  const modalIframe = document.getElementById('modal-iframe');
  document.querySelectorAll('.webcam-fullscreen').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const iframeURL = e.target.closest('.webcam-card').getAttribute('data-iframe');
      modalIframe.src = iframeURL;
      modal.style.display = 'flex';
    });
  });
  const closeBtn = document.querySelector('.modal-close');
  if (closeBtn) closeBtn.addEventListener('click', () => { modal.style.display = 'none'; modalIframe.src = ''; });
  if (modal) modal.addEventListener('click', (e) => { if (e.target === modal) { modal.style.display = 'none'; modalIframe.src=''; } });
});
