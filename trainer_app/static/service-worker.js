const CACHE_NAME = 'fitspace-v4';
const STATIC_CACHE = 'fitspace-static-v4';
const DYNAMIC_CACHE = 'fitspace-dynamic-v4';

const staticAssets = [
  '/',
  '/static/css/bootstrap.min.css',
  '/static/css/calendario.css',
  '/static/js/bootstrap.bundle.min.js',
  '/static/manifest.json',
  '/static/icons/logo.jpg',
  '/static/icons/logo.png'
];

// Install: cachear assets estáticos
self.addEventListener('install', event => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[SW] Caching static assets');
        return cache.addAll(staticAssets);
      })
      .then(() => self.skipWaiting())
      .catch(err => console.error('[SW] Install error:', err))
  );
});

// Activate: limpiar cachés viejos
self.addEventListener('activate', event => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      console.log('[SW] Cleaning old caches:', cacheNames);
      return Promise.all(
        cacheNames
          .filter(name => name !== STATIC_CACHE && name !== DYNAMIC_CACHE && name !== CACHE_NAME)
          .map(name => {
            console.log('[SW] Deleting cache:', name);
            return caches.delete(name);
          })
      );
    })
    .then(() => self.clients.claim())
  );
});

// Fetch: estrategia de caché inteligente
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);

  // Ignorar requests non-GET
  if (req.method !== 'GET') {
    return;
  }

  // Ignorar requests de otros orígenes (SSRF prevention)
  if (url.origin !== self.location.origin) {
    return;
  }

  // API requests: network-first con fallback a caché
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(req));
  }
  // Assets estáticos: cache-first
  else if (
    url.pathname.startsWith('/static/') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.js')
  ) {
    event.respondWith(cacheFirst(req));
  }
  // Navegación: stale-while-revalidate
  else {
    event.respondWith(staleWhileRevalidate(req));
  }
});

// Estrategia: Cache First
function cacheFirst(req) {
  return caches.match(req).then(cached => {
    if (cached) {
      console.log('[SW] Cache hit:', req.url);
      return cached;
    }
    
    return fetch(req)
      .then(response => {
        if (!response || response.status !== 200 || response.type === 'basic') {
          return response;
        }
        
        const responseToCache = response.clone();
        caches.open(STATIC_CACHE).then(cache => {
          cache.put(req, responseToCache);
        });
        
        return response;
      })
      .catch(err => {
        console.error('[SW] Fetch failed:', req.url, err);
        return caches.match(req) || new Response('Offline - Resource not available', {
          status: 503,
          statusText: 'Service Unavailable'
        });
      });
  });
}

// Estrategia: Network First
function networkFirst(req) {
  return fetch(req)
    .then(response => {
      if (!response || response.status !== 200) {
        return response;
      }
      
      const responseToCache = response.clone();
      caches.open(DYNAMIC_CACHE).then(cache => {
        cache.put(req, responseToCache);
      });
      
      console.log('[SW] Network fresh:', req.url);
      return response;
    })
    .catch(err => {
      console.log('[SW] Network failed, using cache:', req.url);
      return caches.match(req).catch(() => {
        return new Response(JSON.stringify({
          error: 'Offline',
          message: 'No cached response available'
        }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' }
        });
      });
    });
}

// Estrategia: Stale While Revalidate
function staleWhileRevalidate(req) {
  return caches.match(req).then(cached => {
    const fetchPromise = fetch(req).then(response => {
      if (!response || response.status !== 200) {
        return response;
      }
      
      const responseToCache = response.clone();
      caches.open(DYNAMIC_CACHE).then(cache => {
        cache.put(req, responseToCache);
      });
      
      return response;
    })
    .catch(err => {
      console.error('[SW] Fetch error for stale-while-revalidate:', err);
      return new Response('Offline', { status: 503 });
    });

    return cached || fetchPromise;
  });
}

// Manejar notificaciones push
self.addEventListener('push', event => {
  const options = {
    body: 'Tienes una nueva notificación de Fitspace',
    icon: '/static/icons/logo.jpg',
    badge: '/static/icons/logo.jpg',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Ver detalles',
        icon: '/static/icons/logo.jpg'
      },
      {
        action: 'close',
        title: 'Cerrar',
        icon: '/static/icons/logo.jpg'
      }
    ]
  };

  if (event.data) {
    try {
      const data = event.data.json();
      options.body = data.message || options.body;
      options.data = { ...options.data, ...data.data };
    } catch (e) {
      console.error('Error parsing push data:', e);
    }
  }

  event.waitUntil(
    self.registration.showNotification('Fitspace', options)
  );
});

// Manejar clicks en notificaciones
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  } else if (event.action === 'close') {
    return;
  } else {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});
