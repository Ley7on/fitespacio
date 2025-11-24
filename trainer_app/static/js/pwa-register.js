// Guardar en: backend/trainer_app/static/js/pwa-register.js
// Script mejorado para registrar el service worker

(function() {
  console.log('[PWA] Iniciando registro de Service Worker...');

  if (!('serviceWorker' in navigator)) {
    console.warn('[PWA] Service Workers no soportados');
    return;
  }

  // TEMPORALMENTE DESHABILITADO - El SW interfiere con redirects en raíz
  return;

  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/service-worker.js', {
      scope: '/'
    })
    .then(registration => {
      console.log('[PWA] ✓ Service Worker registrado:', registration.scope);
      
      // Monitorear actualizaciones
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        console.log('[PWA] Nueva versión del Service Worker detectada');
        
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            console.log('[PWA] ✓ Nueva versión disponible');
            // Notificar al usuario que hay actualización
            window.dispatchEvent(new Event('sw-updated'));
          }
        });
      });

      // Verificar periódicamente si hay actualizaciones
      setInterval(() => {
        registration.update();
      }, 60000); // Cada minuto

    })
    .catch(error => {
      console.error('[PWA] ✗ Error registrando Service Worker:', error);
    });

    // Manejar actualizaciones del SW
    let refreshing = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (refreshing) return;
      refreshing = true;
      console.log('[PWA] Recargando página con nueva versión...');
      window.location.reload();
    });
  });

  // Evento para instalación
  let deferredPrompt;
  window.addEventListener('beforeinstallprompt', (e) => {
    console.log('[PWA] ✓ Aplicación es instalable');
    e.preventDefault();
    deferredPrompt = e;
    
    // Mostrar botón de instalación si existe
    const installBtn = document.getElementById('install-app-btn');
    if (installBtn) {
      installBtn.style.display = 'flex';
      installBtn.addEventListener('click', async () => {
        if (deferredPrompt) {
          deferredPrompt.prompt();
          const { outcome } = await deferredPrompt.userChoice;
          console.log(`[PWA] Usuario ${outcome === 'accepted' ? 'instaló' : 'rechazó'} la app`);
          deferredPrompt = null;
        }
      });
    }
  });

  window.addEventListener('appinstalled', () => {
    console.log('[PWA] ✓ Aplicación instalada en dispositivo');
    deferredPrompt = null;
  });

  // Conectividad
  window.addEventListener('online', () => {
    console.log('[PWA] → Online');
    window.dispatchEvent(new Event('app-online'));
  });

  window.addEventListener('offline', () => {
    console.log('[PWA] → Offline');
    window.dispatchEvent(new Event('app-offline'));
  });

})();
