/**
 * ui-premium.js — WhaleX Prime
 * ═══════════════════════════════════════════════════════════
 * تحسينات UI/UX متقدمة
 * ═══════════════════════════════════════════════════════════
 */

const UI_PREMIUM = {
  
  // ── Loading Skeletons ─────────────────
  showSkeleton(container, count = 3, type = 'signal') {
    const skeletons = {
      signal: `
        <div class="signal-card skeleton-wrapper" style="padding: 16px; margin: 8px 16px;">
          <div class="skeleton" style="height: 60px; width: 100%; border-radius: 12px;"></div>
        </div>
      `,
      stat: `
        <div class="stat-card">
          <div class="skeleton" style="height: 32px; width: 60%; margin: 0 auto 8px; border-radius: 8px;"></div>
          <div class="skeleton" style="height: 12px; width: 40%; margin: 0 auto; border-radius: 4px;"></div>
        </div>
      `,
    };
    
    const html = Array(count).fill(skeletons[type] || skeletons.signal).join('');
    if (container) container.innerHTML = html;
  },
  
  // ── Haptic Feedback ──────────────────
  vibrate(duration = 10) {
    if (window.navigator && window.navigator.vibrate) {
      window.navigator.vibrate(duration);
    }
  },
  
  // ── Confetti Effect (للإنجازات) ──────
  showConfetti() {
    if (typeof confetti === 'function') {
      confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#00f5ff', '#9d4edd', '#ff66c4', '#00ff88']
      });
    } else {
      // Simple fallback
      console.log('🎉 Achievement unlocked!');
    }
  },
  
  // ── Toast Premium ─────────────────────
  toast(message, type = 'info', duration = 3000) {
    const toast = document.getElementById('premium-toast');
    if (!toast) {
      this._createToastContainer();
    }
    
    const toastEl = document.getElementById('premium-toast');
    toastEl.textContent = message;
    toastEl.className = `toast toast-${type} show`;
    
    setTimeout(() => {
      toastEl.classList.remove('show');
    }, duration);
  },
  
  _createToastContainer() {
    const toast = document.createElement('div');
    toast.id = 'premium-toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  },
  
  // ── Modal with Animation ──────────────
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    modal.classList.add('open');
    this.vibrate(5);
    
    // Focus first input
    setTimeout(() => {
      const input = modal.querySelector('input, select, textarea');
      if (input) input.focus();
    }, 100);
  },
  
  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('open');
  },
  
  // ── Page Transitions ──────────────────
  transitionPage(fromScreen, toScreen, callback) {
    const fromEl = document.getElementById(fromScreen);
    const toEl = document.getElementById(toScreen);
    
    if (fromEl) {
      fromEl.style.animation = 'slideOut 0.2s ease forwards';
    }
    
    setTimeout(() => {
      if (fromEl) fromEl.classList.remove('show');
      if (toEl) {
        toEl.classList.add('show');
        toEl.style.animation = 'fadeIn 0.3s ease forwards';
      }
      if (callback) callback();
    }, 200);
  },
  
  // ── Number Animation (Counter) ────────
  animateNumber(element, start, end, duration = 1000) {
    if (!element) return;
    
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
      current += increment;
      if (current >= end) {
        element.textContent = end.toLocaleString();
        clearInterval(timer);
      } else {
        element.textContent = Math.floor(current).toLocaleString();
      }
    }, 16);
  },
  
  // ── Pull to Refresh ───────────────────
  initPullToRefresh(containerId, onRefresh) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    let startY = 0;
    let pulling = false;
    
    container.addEventListener('touchstart', (e) => {
      if (container.scrollTop === 0) {
        startY = e.touches[0].clientY;
        pulling = true;
      }
    });
    
    container.addEventListener('touchmove', (e) => {
      if (!pulling) return;
      const diff = e.touches[0].clientY - startY;
      if (diff > 50) {
        pulling = false;
        this.toast('🔄 تحديث البيانات...', 'info');
        onRefresh();
      }
    });
    
    container.addEventListener('touchend', () => {
      pulling = false;
    });
  },
  
  // ── Scroll to Top Button ──────────────
  initScrollToTop(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const btn = document.createElement('div');
    btn.className = 'scroll-top-btn';
    btn.innerHTML = '↑';
    btn.style.cssText = `
      position: fixed;
      bottom: 90px;
      right: 16px;
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: var(--gradient-primary);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      opacity: 0;
      transition: all 0.3s;
      z-index: 99;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    document.body.appendChild(btn);
    
    container.addEventListener('scroll', () => {
      if (container.scrollTop > 200) {
        btn.style.opacity = '1';
      } else {
        btn.style.opacity = '0';
      }
    });
    
    btn.addEventListener('click', () => {
      container.scrollTo({ top: 0, behavior: 'smooth' });
    });
  },
  
  // ── Swipe Navigation ──────────────────
  initSwipeNavigation(containerId, onSwipeLeft, onSwipeRight) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    let touchStartX = 0;
    let touchEndX = 0;
    
    container.addEventListener('touchstart', (e) => {
      touchStartX = e.changedTouches[0].screenX;
    });
    
    container.addEventListener('touchend', (e) => {
      touchEndX = e.changedTouches[0].screenX;
      const diff = touchEndX - touchStartX;
      
      if (Math.abs(diff) > 50) {
        if (diff > 0 && onSwipeRight) onSwipeRight();
        if (diff < 0 && onSwipeLeft) onSwipeLeft();
      }
    });
  },
  
  // ── Lazy Loading Images ───────────────
  lazyLoadImages() {
    const images = document.querySelectorAll('img[data-src]');
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          img.removeAttribute('data-src');
          observer.unobserve(img);
        }
      });
    });
    
    images.forEach(img => observer.observe(img));
  },
};