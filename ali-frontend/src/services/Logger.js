import api from '../api/axiosInterceptor';

class LoggerService {
    constructor() {
        this.buffer = [];
        this.isFlushing = false;
    }

    /**
     * Log an error message
     * @param {string} message - Error message
     * @param {string} component - Component where error occurred
     * @param {string} stack - Stack trace (optional)
     * @param {object} meta - Additional metadata
     */
    error(message, component = "App", stack = null, meta = {}) {
        this._log("error", message, component, stack, meta);
    }

    /**
     * Log an info message
     */
    info(message, component = "App", meta = {}) {
        this._log("info", message, component, null, meta);
    }

    _log(level, message, component, stack, meta) {
        const entry = {
            level,
            message,
            component,
            stack: stack || new Error().stack,
            meta,
            timestamp: new Date().toISOString()
        };

        // If high severity (error), send immediately
        if (level === 'error') {
            this._send(entry);
        } else {
            // Buffer info logs (stub for now, just send)
            this._send(entry);
        }
    }

    async _send(entry) {
        try {
            await api.post('/api/monitoring/logs/client', entry);
        } catch (e) {
            // Fallback: console log if backend unreachable to avoid infinite loops
            console.error("LoggerService failed to send log:", e);
        }
    }
}

const Logger = new LoggerService();
export default Logger;
