// Sistema de Notificaciones Push para Chat
class NotificationSystem {
    constructor() {
        this.permission = 'default';
        this.isSupported = 'Notification' in window;
        this.soundEnabled = true;
        this.init();
    }

    async init() {
        if (!this.isSupported) {
            console.warn('Notifications not supported');
            return;
        }

        // Solicitar permisos si no los tiene
        if (Notification.permission === 'default') {
            this.permission = await Notification.requestPermission();
        } else {
            this.permission = Notification.permission;
        }

        // Crear audio para notificaciones
        this.notificationSound = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT');
    }

    canShowNotifications() {
        return this.isSupported && this.permission === 'granted';
    }

    showChatNotification(senderName, message, senderType = 'entrenador') {
        if (!this.canShowNotifications()) {
            console.log('Cannot show notification - permission denied or not supported');
            return;
        }

        const icon = senderType === 'entrenador' ? '👨🏫' : senderType === 'system' ? '🤖' : '👤';
        const title = `${icon} ${senderName}`;
        const truncatedMessage = message.length > 100 ? message.substring(0, 100) + '...' : message;

        const notification = new Notification(title, {
            body: truncatedMessage,
            icon: '/static/icons/logo.jpg',
            badge: '/static/icons/logo.jpg',
            tag: `chat-${senderType}`,
            requireInteraction: false,
            silent: false,
            timestamp: Date.now(),
            data: {
                senderType: senderType,
                timestamp: new Date().toISOString()
            }
        });

        // Auto cerrar después de 5 segundos
        setTimeout(() => {
            notification.close();
        }, 5000);

        // Reproducir sonido
        if (this.soundEnabled) {
            this.playNotificationSound();
        }

        // Manejar click en notificación
        notification.onclick = () => {
            window.focus();
            notification.close();
            
            // Redirigir al chat si no está ya ahí
            if (!window.location.pathname.includes('/chat/')) {
                if (senderType === 'entrenador') {
                    window.location.href = '/alumno/chat/entrenador/';
                }
            }
        };

        return notification;
    }

    showSystemNotification(title, message, type = 'info') {
        if (!this.canShowNotifications()) {
            return;
        }

        const icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'fitness': '💪'
        };

        const notification = new Notification(`${icons[type] || 'ℹ️'} ${title}`, {
            body: message,
            icon: '/static/icons/logo.jpg',
            tag: `system-${type}`,
            requireInteraction: type === 'error',
            silent: type === 'info'
        });

        setTimeout(() => {
            notification.close();
        }, type === 'error' ? 10000 : 5000);

        if (this.soundEnabled && type !== 'info') {
            this.playNotificationSound();
        }

        return notification;
    }

    playNotificationSound() {
        try {
            this.notificationSound.currentTime = 0;
            this.notificationSound.play().catch(e => {
                console.log('Could not play notification sound:', e);
            });
        } catch (e) {
            console.log('Notification sound error:', e);
        }
    }

    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        localStorage.setItem('notificationSound', this.soundEnabled);
        return this.soundEnabled;
    }

    // Mostrar notificación in-app (fallback)
    showInAppNotification(title, message, type = 'info') {
        const container = this.getOrCreateInAppContainer();
        
        const notification = document.createElement('div');
        notification.className = `in-app-notification notification-${type} show`;
        
        const icons = {
            'info': 'fa-info-circle',
            'success': 'fa-check-circle',
            'warning': 'fa-exclamation-triangle',
            'error': 'fa-times-circle',
            'chat': 'fa-comment'
        };

        notification.innerHTML = `
            <div class="notification-content">
                <i class="fa-solid ${icons[type] || 'fa-bell'} notification-icon"></i>
                <div class="notification-text">
                    <div class="notification-title">${this.sanitizeHTML(title)}</div>
                    <div class="notification-message">${this.sanitizeHTML(message)}</div>
                </div>
                <button class="notification-close" onclick="this.parentElement.remove()">
                    <i class="fa-solid fa-times"></i>
                </button>
            </div>
        `;

        container.appendChild(notification);

        // Auto remove después de 5 segundos
        setTimeout(() => {
            if (notification.parentElement) {
                notification.classList.remove('show');
                setTimeout(() => notification.remove(), 300);
            }
        }, 5000);

        return notification;
    }

    getOrCreateInAppContainer() {
        let container = document.getElementById('inAppNotifications');
        if (!container) {
            container = document.createElement('div');
            container.id = 'inAppNotifications';
            container.className = 'in-app-notifications-container';
            document.body.appendChild(container);
        }
        return container;
    }

    sanitizeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Método principal para mostrar notificaciones
    notify(title, message, type = 'info', senderType = null) {
        // Intentar notificación nativa primero
        if (this.canShowNotifications()) {
            if (senderType) {
                return this.showChatNotification(title, message, senderType);
            } else {
                return this.showSystemNotification(title, message, type);
            }
        } else {
            // Fallback a notificación in-app
            return this.showInAppNotification(title, message, type);
        }
    }
}

// CSS para notificaciones in-app
const notificationCSS = `
.in-app-notifications-container {
    position: fixed;
    top: 80px;
    right: 20px;
    z-index: 9999;
    max-width: 350px;
}

.in-app-notification {
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 12px;
    margin-bottom: 10px;
    opacity: 0;
    transform: translateX(100%);
    transition: all 0.3s ease;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.in-app-notification.show {
    opacity: 1;
    transform: translateX(0);
}

.notification-content {
    display: flex;
    align-items: flex-start;
    padding: 1rem;
    gap: 0.75rem;
}

.notification-icon {
    font-size: 1.25rem;
    margin-top: 0.25rem;
    flex-shrink: 0;
}

.notification-text {
    flex: 1;
    min-width: 0;
}

.notification-title {
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 0.25rem;
    font-size: 0.9rem;
}

.notification-message {
    color: #ccc;
    font-size: 0.85rem;
    line-height: 1.4;
}

.notification-close {
    background: none;
    border: none;
    color: #888;
    cursor: pointer;
    padding: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: all 0.2s ease;
    flex-shrink: 0;
}

.notification-close:hover {
    background: #333;
    color: #fff;
}

.notification-info .notification-icon { color: #00d4aa; }
.notification-success .notification-icon { color: #28a745; }
.notification-warning .notification-icon { color: #ffc107; }
.notification-error .notification-icon { color: #dc3545; }
.notification-chat .notification-icon { color: #007bff; }

@media (max-width: 768px) {
    .in-app-notifications-container {
        top: 70px;
        right: 10px;
        left: 10px;
        max-width: none;
    }
    
    .notification-content {
        padding: 0.75rem;
    }
}
`;

// Inyectar CSS
const style = document.createElement('style');
style.textContent = notificationCSS;
document.head.appendChild(style);

// Crear instancia global
window.notificationSystem = new NotificationSystem();

// Función helper global
window.showNotification = (title, message, type = 'info', senderType = null) => {
    return window.notificationSystem.notify(title, message, type, senderType);
};

// Solicitar permisos al cargar
document.addEventListener('DOMContentLoaded', () => {
    // Solicitar permisos después de 3 segundos para mejor UX
    setTimeout(() => {
        if (window.notificationSystem.permission === 'default') {
            window.notificationSystem.init();
        }
    }, 3000);
});
