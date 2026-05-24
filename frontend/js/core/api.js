/**
 * api.js — WhaleX Prime
 * ══════════════════════════════════════
 * جميع طلبات HTTP - متصلة بـ Backend الحقيقي
 * ══════════════════════════════════════
 */

const API = {
  
  _token: null,
  
  setToken(token) {
    this._token = token;
    if (token) {
      STATE.save('token', token);
    }
  },
  
  _headers() {
    const h = { 'Content-Type': 'application/json' };
    const token = this._token || STATE.token;
    if (token) {
      h.Authorization = 'Bearer ' + token;
    }
    return h;
  },

  async _get(path) {
    try {
      const url = CONFIG.API + path;
      const r = await fetch(url, { headers: this._headers() });
      if (!r.ok) {
        if (r.status === 401) {
          // Token expired - need to re-authenticate
          localStorage.removeItem('wx_tok');
          window.location.reload();
        }
        return null;
      }
      return r.json();
    } catch (err) {
      console.error('API GET error:', path, err);
      return null;
    }
  },

  async _post(path, body) {
    try {
      const url = CONFIG.API + path;
      const r = await fetch(url, {
        method: 'POST',
        headers: this._headers(),
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        if (r.status === 401) {
          localStorage.removeItem('wx_tok');
          window.location.reload();
        }
        return null;
      }
      return r.json();
    } catch (err) {
      console.error('API POST error:', path, err);
      return null;
    }
  },

  // ── Auth ─────────────────────────────
  async guestLogin(name, email) {
    const result = await this._post('/auth/guest', { name, email });
    if (result?.access_token) {
      this.setToken(result.access_token);
      STATE.save('tier', result.tier);
    }
    return result;
  },

  async register(name, email, password, referralCode) {
    const result = await this._post('/auth/register', { name, email, password, referral_code: referralCode });
    if (result?.access_token) {
      this.setToken(result.access_token);
      STATE.save('tier', result.tier);
    }
    return result;
  },

  async login(email, password) {
    const result = await this._post('/auth/login', { email, password });
    if (result?.access_token) {
      this.setToken(result.access_token);
      STATE.save('tier', result.tier);
    }
    return result;
  },

  // ── User ─────────────────────────────
  async getUserProfile() {
    return this._get('/users/me');
  },

  async updateUserProfile(data) {
    return this._put('/users/me', data);
  },

  // ── Signals ──────────────────────────
  async getFuturesSignals() { 
    return this._get('/signals/futures'); 
  },
  
  async getSpotSignals() { 
    return this._get('/signals/spot'); 
  },
  
  async getMemeSignals() { 
    return this._get('/signals/meme'); 
  },

  async getLatestSignals() {
    return this._get('/signals/latest');
  },

  // ── Prices ───────────────────────────
  async getAllPrices() { 
    // Prices come from WebSocket, but we have a fallback
    return this._get('/prices/all'); 
  },

  // ── Trade ────────────────────────────
  async executeTrade(data) { 
    return this._post('/trade/execute', data); 
  },
  
  async forceStop(symbol) { 
    return this._post('/trade/force-stop', { symbol }); 
  },
  
  async getTradeStats() { 
    return this._get('/trade/stats'); 
  },

  async getTradeHistory(limit = 50) {
    return this._get(`/trade/history?limit=${limit}`);
  },

  // ── Wallet ───────────────────────────
  async getAddress(chain) { 
    return this._get(`/wallet/${chain}/address`); 
  },
  
  async generateWallet(chain) { 
    return this._post('/wallet/generate', { chain }); 
  },

  async withdraw(data) {
    return this._post('/wallet/withdraw', data);
  },

  // ── Exchange ─────────────────────────
  async connectExchange(data) { 
    return this._post('/exchange/connect', data); 
  },

  // ── Subscription ─────────────────────
  async upgrade(data) { 
    return this._post('/subscription/upgrade', data); 
  },

  // ── AI ───────────────────────────────
  async chat(messages) { 
    return this._post('/ai/chat', { messages }); 
  },
  
  async scanContract(data) { 
    return this._post('/ai/scan-contract', data); 
  },

  // ── Referral ─────────────────────────
  async getReferralStats() { 
    return this._get('/referral/stats'); 
  },

  async getReferralCode() {
    return this._get('/referral/code');
  },

  async redeemReferral(code) {
    return this._post('/referral/redeem', { code });
  },

  // ── Admin ────────────────────────────
  async verifyAdmin(password) {
    return this._post('/admin/verify', { password });
  },

  async getAdminStats() { 
    return this._get('/admin/stats'); 
  },
  
  async killSwitch() { 
    return this._post('/admin/kill-switch', { confirm: true }); 
  },
};