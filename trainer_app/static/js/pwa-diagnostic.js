// Guardar en: backend/trainer_app/static/js/pwa-diagnostic.js
// Uso: Agregar en base.html para debugging

console.log('%c=== PWA DIAGNOSTIC ===', 'color: #06b6d4; font-size: 16px; font-weight: bold;');

// Test 1: Verificar Service Worker
console.log('%cTest 1: Service Worker', 'color: #10b981; font-weight: bold;');
if ('serviceWorker' in navigator) {
  console.log('✓ Service Worker API disponible');
  
  navigator.serviceWorker.getRegistrations().then(registrations => {
    if (registrations.length > 0) {
      console.log(`✓ Service Worker registrado (${registrations.length})`);
      registrations.forEach((reg, idx) => {
        console.log(`  [${idx}] Scope: ${reg.scope}`);
        console.log(`      State: ${reg.active ? 'ACTIVE' : 'INACTIVE'}`);
      });
    } else {
      console.log('✗ No hay Service Workers registrados');
    }
  }).catch(err => {
    console.error('✗ Error obteniendo registraciones:', err);
  });
} else {
  console.log('✗ Service Worker API NO disponible');
}

// Test 2: Verificar manifest
console.log('%cTest 2: Manifest', 'color: #10b981; font-weight: bold;');
fetch('/static/manifest.json')
  .then(r => {
    console.log(`✓ Manifest encontrado (${r.status})`);
    return r.json();
  })
  .then(manifest => {
    console.log(`  Nombre: ${manifest.name}`);
    console.log(`  Start URL: ${manifest.start_url}`);
    console.log(`  Display: ${manifest.display}`);
    console.log(`  Iconos: ${manifest.icons ? manifest.icons.length : 0}`);
  })
  .catch(err => console.error('✗ Error cargando manifest:', err));

// Test 3: Verificar Cache Storage
console.log('%cTest 3: Cache Storage', 'color: #10b981; font-weight: bold;');
if ('caches' in window) {
  caches.keys().then(cacheNames => {
    console.log(`✓ Cache Storage disponible (${cacheNames.length} cachés)`);
    cacheNames.forEach(name => {
      caches.open(name).then(cache => {
        cache.keys().then(keys => {
          console.log(`  ${name}: ${keys.length} items`);
        });
      });
    });
  }).catch(err => console.error('✗ Error accediendo Cache:', err));
} else {
  console.log('✗ Cache Storage NO disponible');
}

// Test 4: Verificar IndexedDB
console.log('%cTest 4: IndexedDB', 'color: #10b981; font-weight: bold;');
if ('indexedDB' in window) {
  console.log('✓ IndexedDB disponible');
  const req = indexedDB.databases();
  if (req) {
    req.then(dbs => {
      console.log(`  Bases de datos: ${dbs.length}`);
      dbs.forEach(db => {
        console.log(`    - ${db.name}`);
      });
    });
  }
} else {
  console.log('✗ IndexedDB NO disponible');
}

// Test 5: Verificar HTTPS/Local
console.log('%cTest 5: Seguridad', 'color: #10b981; font-weight: bold;');
if (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
  console.log(`✓ Protocolo seguro: ${location.protocol}`);
} else {
  console.log(`✗ PWA requiere HTTPS o localhost, actualmente: ${location.protocol}`);
}

// Test 6: Instalabilidad
console.log('%cTest 6: Instalabilidad', 'color: #10b981; font-weight: bold;');
let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
  console.log('✓ beforeinstallprompt detectado (PWA es instalable)');
  deferredPrompt = e;
  // Mostrar botón de instalación
  const installBtn = document.getElementById('install-app-btn');
  if (installBtn) {
    installBtn.style.display = 'block';
    installBtn.addEventListener('click', () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(choiceResult => {
          if (choiceResult.outcome === 'accepted') {
            console.log('✓ PWA instalada por usuario');
          } else {
            console.log('✗ Usuario rechazó instalación');
          }
          deferredPrompt = null;
        });
      }
    });
  }
});

window.addEventListener('appinstalled', () => {
  console.log('✓ PWA instalada exitosamente');
});

// Test 7: Connectivity
console.log('%cTest 7: Conectividad', 'color: #10b981; font-weight: bold;');
if (navigator.onLine) {
  console.log('✓ Online');
} else {
  console.log('⚠ Offline');
}

window.addEventListener('online', () => console.log('→ Reconectado'));
window.addEventListener('offline', () => console.log('→ Desconectado'));

// Test 8: Notificaciones
console.log('%cTest 8: Notificaciones', 'color: #10b981; font-weight: bold;');
if ('Notification' in window) {
  console.log(`✓ Notificaciones disponibles (${Notification.permission})`);
  if (Notification.permission === 'granted') {
    console.log('  ✓ Permiso de notificaciones otorgado');
  }
} else {
  console.log('✗ Notificaciones NO disponibles');
}

console.log('%c=== DIAGNOSTIC COMPLETO ===', 'color: #06b6d4; font-size: 14px; font-weight: bold;');
