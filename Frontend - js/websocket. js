/**
 * websocket.js — WhaleX Prime
 * ══════════════════════════════════════
 * WebSocket مع Authentication
 * ══════════════════════════════════════
 */

const WS_CLIENT = {
  _ws: null,
  _pingInterval: null,
  _retries: 0,
  _isConnecting: false,

  connect() {
    if (this._ws?.readyState === WebSocket.OPEN) return;
    if (this._isConnecting) return;
    
    this._isConnecting = true;

    // Build URL with token for authentication
    let wsUrl = CONFIG.WS_URL;
    const token = STATE.token;
    if (token) {
      wsUrl += `?token=${encodeURIComponent(token)}`;
    }

    console.log('Connecting WebSocket...');
    this._ws = new WebSocket(wsUrl);

    this._ws.onopen = () => {
      this._isConnecting = false;
      this._retries = 0;
      this._startPing();
      BUS.emit('ws:connected', null);
      console.log('✅ WebSocket connected');
    };

    this._ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        switch(msg.event) {
          case 'prices':
            STATE.prices = msg.data;
            BUS.emit('ws:prices', msg.data);
            break;
          case 'signal':
            BUS.emit('ws:signal', msg.data);
            break;
          case 'ping':
            // Respond to ping
            this.send('pong', { ts: msg.ts });
            break;
          case 'pong':
            // Keep alive confirmed
            break;
          default:
            BUS.emit('ws:' + msg.event, msg.data);
        }
      } catch(err) {
        console.error('WebSocket parse error:', err);
      }
    };

    this._ws.onclose = (e) => {
      this._isConnecting = false;
      this._stopPing();
      BUS.emit('ws:disconnected', null);
      console.log('WebSocket disconnected, reconnecting...');
      this._reconnect();
    };

    this._ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      this._ws?.close();
    };
  },

  send(event, data = {}) {
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify({ event, ...data }));
    } else {
      console.warn('WebSocket not open, cannot send:', event);
    }
  },

  subscribe(symbol) {
    this.send('subscribe', { symbol });
  },

  _startPing() {
    this._pingInterval = setInterval(() => {
      this.send('ping', { ts: Date.now() });
    }, CONFIG.WS_PING_INTERVAL);
  },

  _stopPing() {
    if (this._pingInterval) {
      clearInterval(this._pingInterval);
      this._pingInterval = null;
    }
  },

  _reconnect() {
    this._retries++;
    const delay = Math.min(CONFIG.WS_BASE_RETRY_MS * this._retries, CONFIG.WS_MAX_RETRY_MS);
    console.log(`Reconnecting in ${delay}ms (attempt ${this._retries})`);
    setTimeout(() => this.connect(), delay);
  },

  disconnect() {
    this._stopPing();
    this._ws?.close();
  },
};