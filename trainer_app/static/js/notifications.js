// Sistema de notificaciones push para FitSpace
class NotificationManager {
    constructor() {
        this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
        this.registration = null;
        this.subscription = null;
    }

    async init() {
        if (!this.isSupported) {
            console.warn('Push notifications no soportadas');
            return false;
        }

        try {
            // Registrar service worker
            this.registration = await navigator.serviceWorker.register('/service-worker.js');
            console.log('Service Worker registrado:', this.registration);

            // Solicitar permisos
            const permission = await this.requestPermission();

            // Si no hay permiso concedido, no intentamos suscribir
            if (permission !== 'granted') {
                console.warn('Permiso de notificaciones no concedido, se omite la suscripción');
                return false;
            }

            // Suscribirse a notificaciones
            await this.subscribe();

            return true;
        } catch (error) {
            console.error('Error inicializando notificaciones:', error);
            return false;
        }
    }

    async requestPermission() {
        // Pedir permiso de forma segura; no lanzar excepción si el usuario deniega
        try {
            const permission = await Notification.requestPermission();

            if (permission === 'granted') {
                console.log('Permisos de notificación concedidos');
                this.showWelcomeNotification();
            } else if (permission === 'denied') {
                console.warn('Permisos de notificación denegados');
                // No lanzar error; devolvemos el estado para que el init lo maneje
            } else {
                console.log('Permisos de notificación pendientes');
            }

            return permission;
        } catch (err) {
            console.error('Error solicitando permiso de notificación:', err);
            return 'default';
        }
    }

    async subscribe() {
        if (!this.registration) {
            throw new Error('Service Worker no registrado');
        }

        try {
            // Generar clave VAPID (en producción usar clave real)
            const vapidPublicKey = 'BEl62iUYgUivxIkv69yViEuiBIa40HI0DLLuxazjqAKVXTJtkTXaXWKB4qGufAA1-8aAXHs0VVnLrBc6XrWyVxs';

            this.subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(vapidPublicKey)
            });

            console.log('Suscripción creada:', this.subscription);

            // Enviar suscripción al servidor
            await this.sendSubscriptionToServer();

        } catch (error) {
            console.error('Error suscribiéndose:', error);
            throw error;
        }
    }

    async sendSubscriptionToServer() {
        try {
            const response = await fetch('/notifications/push/register/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    subscription: this.subscription.toJSON()
                })
            });

            const result = await response.json();

            if (result.success) {
                console.log('Suscripción registrada en el servidor');
            } else {
                console.error('Error registrando suscripción:', result.error);
            }
        } catch (error) {
            console.error('Error enviando suscripción al servidor:', error);
        }
    }

    async sendTestNotification() {
        try {
            const response = await fetch('/notifications/push/test/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();

            if (result.success) {
                console.log('Notificación de prueba enviada');
            } else {
                console.error('Error enviando notificación de prueba:', result.error);
            }
        } catch (error) {
            console.error('Error enviando notificación de prueba:', error);
        }
    }

    showWelcomeNotification() {
        if (Notification.permission === 'granted') {
            new Notification('¡Bienvenido a FitSpace!', {
                body: 'Las notificaciones están activadas. Te mantendremos informado.',
                icon: '/static/icons/logo.jpg',
                badge: '/static/icons/logo.jpg'
            });
        }
    }

    showLocalNotification(title, options = {}) {
        if (Notification.permission === 'granted') {
            const defaultOptions = {
                icon: '/static/icons/logo.jpg',
                badge: '/static/icons/logo.jpg',
                vibrate: [100, 50, 100]
            };

            new Notification(title, { ...defaultOptions, ...options });
        }
    }

    // Utilidades
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    getCSRFToken() {
        // First try hidden input (if present in page templates)
        try {
            const el = document.querySelector('[name=csrfmiddlewaretoken]');
            if (el && el.value) return el.value;
        } catch (e) {}

        // Then try common cookie names (backwards compatible)
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'trainer_csrftoken' || name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', async () => {
    const notificationManager = new NotificationManager();
    
    // Intentar inicializar automáticamente
    const initialized = await notificationManager.init();
    
    if (initialized) {
        console.log('Sistema de notificaciones inicializado correctamente');
        
        // Hacer disponible globalmente para testing
        window.notificationManager = notificationManager;
    }
});

// Helper global para mostrar notificaciones desde cualquier JS del frontend.
// Muestra notificación del sistema (si está permitido), añade un toast en página
// y solicita una actualización del contador/lista de mensajes no leídos.
window.showNotification = function(title, body = '', level = 'info') {
    try {
        // Mostrar notificación del sistema si está disponible
        if (window.notificationManager && Notification.permission === 'granted') {
            window.notificationManager.showLocalNotification(title, { body });
        } else if (Notification.permission === 'granted') {
            // Fallback simple
            new Notification(title, { body, icon: '/static/icons/logo.jpg' });
        }

        // Crear toast en página (lightweight)
        try {
            let container = document.getElementById('fs_notification_container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'fs_notification_container';
                container.style.position = 'fixed';
                container.style.top = '1rem';
                container.style.right = '1rem';
                container.style.zIndex = 99999;
                document.body.appendChild(container);
            }

            const toast = document.createElement('div');
            toast.className = 'fs-toast-notification';
            toast.style.background = '#0d1b1a';
            toast.style.color = 'white';
            toast.style.padding = '12px 16px';
            toast.style.marginTop = '8px';
            toast.style.borderRadius = '8px';
            toast.style.boxShadow = '0 6px 18px rgba(0,0,0,0.4)';
            toast.style.maxWidth = '320px';
            toast.style.fontSize = '14px';

            toast.innerHTML = `<strong style="display:block;margin-bottom:6px">${title}</strong><div style="opacity:0.9">${body}</div>`;

            container.appendChild(toast);

            setTimeout(() => {
                toast.style.transition = 'opacity 0.4s, transform 0.4s';
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-8px)';
                setTimeout(() => toast.remove(), 450);
            }, 5000);
        } catch (e) {
            console.warn('No se pudo renderizar toast en página', e);
        }

        // Intentar actualizar contador y lista de mensajes en la UI
        try {
            if (typeof cargarMensajesNoLeidos === 'function') {
                cargarMensajesNoLeidos();
            } else {
                // intentar llamar al endpoint para forzar recarga desde templates que no importen la función
                fetch('/alumno/api/mensajes-no-leidos/').catch(()=>{});
            }
        } catch (e) {}

    } catch (err) {
        console.error('showNotification error', err);
    }
};

// Inserta un mensaje recibido (objeto mensaje {id,titulo,contenido,tipo,prioridad,fecha_envio})
window.handleIncomingMensaje = function(mensaje) {
    try {
        if (!mensaje) return;

        // Actualizar badge
        try {
            const badge = document.getElementById('mensajesBadge');
            if (badge) {
                let count = parseInt(badge.textContent || '0') || 0;
                count = Math.max(1, count + 1);
                badge.textContent = count;
                badge.style.display = 'inline-block';
            }
        } catch (e) {}

        // Formatear hora
        let hora = '';
        try {
            if (mensaje.fecha_envio) {
                const d = new Date(mensaje.fecha_envio);
                hora = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            } else if (mensaje.fecha) {
                hora = mensaje.fecha;
            } else {
                const d = new Date();
                hora = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
        } catch (e) {
            hora = '';
        }

        // Actualizar panel del dashboard
        try {
            const dashboard = document.getElementById('dashboardNotificaciones');
            if (dashboard) {
                // Crear tarjeta de notificación
                const card = document.createElement('div');
                card.className = 'notification-card';
                card.innerHTML = `
                    <div class="notification-title">${escapeHtml(mensaje.titulo)}</div>
                    <div class="notification-message">${escapeHtml(mensaje.contenido)}</div>
                    <div class="notification-date">${hora}</div>
                `;

                // Si el dashboard tenía el estado vacío con un solo contenedor, reemplazarlo
                if (dashboard.dataset.serverRendered === 'true') {
                    dashboard.dataset.serverRendered = 'false';
                }

                // Prepend y limitar a 3 elementos visuales
                dashboard.insertBefore(card, dashboard.firstChild);
                const cards = dashboard.querySelectorAll('.notification-card');
                if (cards.length > 3) {
                    cards[cards.length-1].remove();
                }
            }
        } catch (e) {
            console.warn('No se pudo actualizar dashboard con el mensaje entrante', e);
        }

        // Actualizar página de mensajes si está abierta
        try {
            const lista = document.getElementById('mensajesContainer');
            if (lista) {
                // Si existía el estado "No hay mensajes", limpiarlo
                const empty = lista.querySelector('.glass > h5');
                if (empty && empty.textContent && empty.textContent.toLowerCase().includes('no hay mensajes')) {
                    lista.innerHTML = '';
                }

                const msg = document.createElement('div');
                msg.className = 'mensaje-card mb-3 mensaje-no-leido';
                msg.dataset.mensajeId = mensaje.id || `m-${Date.now()}`;
                msg.innerHTML = `
                    <div class="glass p-4">
                        <div class="d-flex align-items-start">
                            <div class="mensaje-icon me-3">
                                <i class="fa-solid fa-bell fa-2x text-info"></i>
                            </div>
                            <div class="flex-grow-1">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <h5 class="text-white mb-1">${escapeHtml(mensaje.titulo)}</h5>
                                    <div class="d-flex align-items-center gap-2">
                                        <span class="badge badge-${mensaje.tipo}">${mensaje.tipo}</span>
                                    </div>
                                </div>
                                <p class="text-light-70 mb-3">${escapeHtml(mensaje.contenido)}</p>
                                <div class="d-flex justify-content-between align-items-center">
                                    <small class="text-light-50"><i class="fa-solid fa-clock me-1"></i>${hora} atrás</small>
                                    <div class="mensaje-acciones">
                                        <button class="btn btn-glass btn-sm ms-2" onclick="marcarLeidoTemp(this, '${mensaje.id}')">
                                            <i class="fa-solid fa-check me-1"></i>Marcar como leído
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;

                lista.insertBefore(msg, lista.firstChild);
            }
        } catch (e) {
            console.warn('No se pudo insertar mensaje en la lista de mensajes', e);
        }

    } catch (err) {
        console.error('handleIncomingMensaje error', err);
    }
};

// Helper para escapar HTML simple
function escapeHtml(unsafe) {
    if (!unsafe && unsafe !== 0) return '';
    return String(unsafe)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
}

// Marcar temporalmente como leído (cliente) y llamar al backend
window.marcarLeidoTemp = function(btn, mensajeId) {
    try {
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        fetch(`/alumno/mensajes/${mensajeId}/leido/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken }
        }).then(r => r.json()).then(data => {
            if (data.success) {
                const card = btn.closest('.mensaje-card');
                if (card) card.classList.remove('mensaje-no-leido');
                btn.style.display = 'none';
            }
        }).catch(()=>{});
    } catch(e){}
};

// Función para agregar botón de prueba en desarrollo
// NOTE: El botón de prueba se eliminó deliberadamente para evitar mostrarlo en el panel/dashboard.
// Si se necesita volver a habilitar en desarrollo, reimplemente aquí y controle su aparición por una
// variable de entorno o setting en vez de basarse en hostname.