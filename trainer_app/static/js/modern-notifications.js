// Sistema de Notificaciones Modernas
class ModernNotificationSystem {
    constructor() {
        this.permission = 'default';
        this.isSupported = 'Notification' in window;
        this.soundEnabled = true;
        this.notifications = [];
        this.init();
        this.injectCSS();
    }

    async init() {
        if (!this.isSupported) return;
        
        if (Notification.permission === 'default') {
            this.permission = await Notification.requestPermission();
        } else {
            this.permission = Notification.permission;
        }
    }

    showNotification(title, message, type = 'info', options = {}) {
        // Mostrar notificación nativa si está disponible
        if (this.permission === 'granted' && !options.forceInApp) {
            this.showNativeNotification(title, message, type);
        }
        
        // Siempre mostrar notificación in-app también
        return this.showModernNotification(title, message, type, options);
    }

    showNativeNotification(title, message, type) {
        const icons = {
            'info': '💡',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'chat': '💬'
        };

        new Notification(`${icons[type] || '📱'} ${title}`, {
            body: message,
            icon: '/static/icons/logo.jpg',
            tag: `fittracker-${type}`,
            requireInteraction: type === 'error'
        });
    }

    showModernNotification(title, message, type = 'info', options = {}) {
        const container = this.getOrCreateContainer();
        
        const notification = document.createElement('div');
        notification.className = `modern-toast toast-${type}`;
        
        const icons = {
            'info': { icon: 'fa-info-circle', color: '#00d4aa' },
            'success': { icon: 'fa-check-circle', color: '#28a745' },
            'warning': { icon: 'fa-exclamation-triangle', color: '#ffc107' },
            'error': { icon: 'fa-times-circle', color: '#dc3545' },
            'chat': { icon: 'fa-comment-dots', color: '#007bff' }
        };

        const iconData = icons[type] || icons['info'];
        const duration = options.duration || (type === 'error' ? 8000 : 4000);

        notification.innerHTML = `
            <div class="toast-content">
                <div class="toast-icon" style="color: ${iconData.color}">
                    <i class="fa-solid ${iconData.icon}"></i>
                </div>
                <div class="toast-body">
                    <div class="toast-title">${this.sanitizeHTML(title)}</div>
                    <div class="toast-message">${this.sanitizeHTML(message)}</div>
                </div>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fa-solid fa-times"></i>
                </button>
            </div>
            <div class="toast-progress" style="background: ${iconData.color}"></div>
        `;

        container.appendChild(notification);

        // Animación de entrada
        requestAnimationFrame(() => {
            notification.classList.add('show');
        });

        // Auto remove
        setTimeout(() => {
            notification.classList.add('hide');
            setTimeout(() => notification.remove(), 300);
        }, duration);

        // Sonido
        if (this.soundEnabled && type !== 'info') {
            this.playSound();
        }

        return notification;
    }

    getOrCreateContainer() {
        let container = document.getElementById('modernNotifications');
        if (!container) {
            container = document.createElement('div');
            container.id = 'modernNotifications';
            container.className = 'modern-notifications-container';
            document.body.appendChild(container);
        }
        return container;
    }

    playSound() {
        // Sonido sutil para notificaciones
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
        
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.2);
    }

    sanitizeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    injectCSS() {
        const css = `
        .modern-notifications-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
            pointer-events: none;
        }

        .modern-toast {
            background: rgba(26, 26, 26, 0.95);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            margin-bottom: 12px;
            opacity: 0;
            transform: translateX(100%) scale(0.8);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            overflow: hidden;
            pointer-events: auto;
            position: relative;
            min-width: 320px;
        }

        .modern-toast.show {
            opacity: 1;
            transform: translateX(0) scale(1);
        }

        .modern-toast.hide {
            opacity: 0;
            transform: translateX(100%) scale(0.8);
        }

        .toast-content {
            display: flex;
            align-items: flex-start;
            padding: 16px;
            gap: 12px;
        }

        .toast-icon {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            flex-shrink: 0;
            background: rgba(255, 255, 255, 0.1);
        }

        .toast-body {
            flex: 1;
            min-width: 0;
        }

        .toast-title {
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 4px;
            font-size: 14px;
            line-height: 1.3;
        }

        .toast-message {
            color: rgba(255, 255, 255, 0.8);
            font-size: 13px;
            line-height: 1.4;
            margin: 0;
        }

        .toast-close {
            background: none;
            border: none;
            color: rgba(255, 255, 255, 0.5);
            cursor: pointer;
            padding: 6px;
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            transition: all 0.2s ease;
            flex-shrink: 0;
            font-size: 12px;
        }

        .toast-close:hover {
            background: rgba(255, 255, 255, 0.1);
            color: rgba(255, 255, 255, 0.8);
        }

        .toast-progress {
            position: absolute;
            bottom: 0;
            left: 0;
            height: 3px;
            width: 100%;
            animation: toastProgress 4s linear forwards;
        }

        @keyframes toastProgress {
            from { width: 100%; }
            to { width: 0%; }
        }

        .modern-toast:hover .toast-progress {
            animation-play-state: paused;
        }

        .modern-toast:hover {
            transform: translateX(-8px) scale(1.02);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.4);
        }

        @media (max-width: 768px) {
            .modern-notifications-container {
                top: 80px;
                right: 16px;
                left: 16px;
                max-width: none;
            }
            
            .modern-toast {
                min-width: auto;
            }
            
            .toast-content {
                padding: 14px;
            }
            
            .toast-icon {
                width: 36px;
                height: 36px;
                font-size: 16px;
            }
        }
        `;

        const style = document.createElement('style');
        style.textContent = css;
        document.head.appendChild(style);
    }
}

// Crear instancia global
window.modernNotifications = new ModernNotificationSystem();

// Función helper global mejorada
window.showNotification = (title, message, type = 'info', options = {}) => {
    return window.modernNotifications.showNotification(title, message, type, options);
};

// Auto-inicializar
document.addEventListener('DOMContentLoaded', () => {
    // Solicitar permisos después de interacción del usuario
    document.addEventListener('click', () => {
        if (window.modernNotifications.permission === 'default') {
            window.modernNotifications.init();
        }
    }, { once: true });
});