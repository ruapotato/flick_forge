/**
 * Flick Store - Main JavaScript
 * Handles UI interactions, navigation, and common functionality
 */

// ==================
// DOM Ready Handler
// ==================

document.addEventListener('DOMContentLoaded', () => {
  initMobileMenu();
  initSearch();
  initCarousel();
  initModals();
  initToasts();
  initForms();
  initCopyButtons();
  initVoteButtons();
  initLazyLoading();
  checkAuth();
});

// ==================
// Mobile Navigation
// ==================

function initMobileMenu() {
  const menuToggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav');

  if (!menuToggle || !nav) return;

  menuToggle.addEventListener('click', () => {
    nav.classList.toggle('active');
    menuToggle.setAttribute('aria-expanded', nav.classList.contains('active'));
  });

  // Close menu on outside click
  document.addEventListener('click', (e) => {
    if (!nav.contains(e.target) && !menuToggle.contains(e.target)) {
      nav.classList.remove('active');
      menuToggle.setAttribute('aria-expanded', 'false');
    }
  });
}

// ==================
// Search Functionality
// ==================

function initSearch() {
  const searchInputs = document.querySelectorAll('[data-search]');

  searchInputs.forEach(input => {
    let debounceTimer;

    input.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        const query = e.target.value.trim();
        if (query.length >= 2) {
          performSearch(query);
        }
      }, 300);
    });

    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const query = e.target.value.trim();
        if (query) {
          window.location.href = `/browse?q=${encodeURIComponent(query)}`;
        }
      }
    });
  });
}

async function performSearch(query) {
  const resultsContainer = document.querySelector('[data-search-results]');
  if (!resultsContainer) return;

  try {
    resultsContainer.innerHTML = '<div class="loading"><div class="loading-spinner"></div></div>';
    const results = await API.apps.search(query, { limit: 5 });
    renderSearchResults(results, resultsContainer);
  } catch (error) {
    console.error('Search error:', error);
    resultsContainer.innerHTML = '<p class="text-muted">Search failed. Please try again.</p>';
  }
}

function renderSearchResults(results, container) {
  if (!results.apps || results.apps.length === 0) {
    container.innerHTML = '<p class="text-muted">No results found</p>';
    return;
  }

  container.innerHTML = results.apps.map(app => `
    <a href="/app/${app.slug}" class="search-result-item">
      <div class="search-result-icon">${app.icon || app.name[0]}</div>
      <div class="search-result-info">
        <div class="search-result-name">${escapeHtml(app.name)}</div>
        <div class="search-result-category">${escapeHtml(app.category)}</div>
      </div>
    </a>
  `).join('');
}

// ==================
// Carousel
// ==================

function initCarousel() {
  const carousels = document.querySelectorAll('.carousel');

  carousels.forEach(carousel => {
    const track = carousel.querySelector('.carousel-track');
    const slides = carousel.querySelectorAll('.carousel-slide');
    const prevBtn = carousel.querySelector('.carousel-nav.prev .carousel-btn');
    const nextBtn = carousel.querySelector('.carousel-nav.next .carousel-btn');
    const dotsContainer = carousel.querySelector('.carousel-dots');

    if (!track || slides.length === 0) return;

    let currentIndex = 0;
    const totalSlides = slides.length;

    // Create dots
    if (dotsContainer) {
      slides.forEach((_, i) => {
        const dot = document.createElement('button');
        dot.className = `carousel-dot ${i === 0 ? 'active' : ''}`;
        dot.setAttribute('aria-label', `Go to slide ${i + 1}`);
        dot.addEventListener('click', () => goToSlide(i));
        dotsContainer.appendChild(dot);
      });
    }

    function goToSlide(index) {
      currentIndex = index;
      track.style.transform = `translateX(-${currentIndex * 100}%)`;

      // Update dots
      const dots = dotsContainer?.querySelectorAll('.carousel-dot');
      dots?.forEach((dot, i) => {
        dot.classList.toggle('active', i === currentIndex);
      });
    }

    function nextSlide() {
      goToSlide((currentIndex + 1) % totalSlides);
    }

    function prevSlide() {
      goToSlide((currentIndex - 1 + totalSlides) % totalSlides);
    }

    prevBtn?.addEventListener('click', prevSlide);
    nextBtn?.addEventListener('click', nextSlide);

    // Auto-advance every 5 seconds
    let autoplayInterval = setInterval(nextSlide, 5000);

    // Pause on hover
    carousel.addEventListener('mouseenter', () => {
      clearInterval(autoplayInterval);
    });

    carousel.addEventListener('mouseleave', () => {
      autoplayInterval = setInterval(nextSlide, 5000);
    });

    // Touch/swipe support
    let touchStartX = 0;
    let touchEndX = 0;

    track.addEventListener('touchstart', (e) => {
      touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    track.addEventListener('touchend', (e) => {
      touchEndX = e.changedTouches[0].screenX;
      handleSwipe();
    }, { passive: true });

    function handleSwipe() {
      const diff = touchStartX - touchEndX;
      if (Math.abs(diff) > 50) {
        if (diff > 0) {
          nextSlide();
        } else {
          prevSlide();
        }
      }
    }
  });
}

// ==================
// Modals
// ==================

function initModals() {
  // Open modal triggers
  document.querySelectorAll('[data-modal-open]').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const modalId = trigger.dataset.modalOpen;
      openModal(modalId);
    });
  });

  // Close modal triggers
  document.querySelectorAll('[data-modal-close]').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const modal = trigger.closest('.modal-overlay');
      if (modal) closeModal(modal.id);
    });
  });

  // Close on overlay click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        closeModal(overlay.id);
      }
    });
  });

  // Close on escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const activeModal = document.querySelector('.modal-overlay.active');
      if (activeModal) closeModal(activeModal.id);
    }
  });
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    // Focus first focusable element
    const focusable = modal.querySelector('button, [href], input, select, textarea');
    focusable?.focus();
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// ==================
// Toast Notifications
// ==================

const toastContainer = document.createElement('div');
toastContainer.className = 'toast-container';
document.body.appendChild(toastContainer);

function initToasts() {
  // Toasts are created dynamically, container already added
}

function showToast(message, type = 'info', duration = 3000) {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${getToastIcon(type)}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
    <button class="toast-close" aria-label="Close">&times;</button>
  `;

  const closeBtn = toast.querySelector('.toast-close');
  closeBtn.addEventListener('click', () => removeToast(toast));

  toastContainer.appendChild(toast);

  // Auto remove
  setTimeout(() => removeToast(toast), duration);
}

function removeToast(toast) {
  toast.style.animation = 'slideOut 0.3s ease forwards';
  setTimeout(() => toast.remove(), 300);
}

function getToastIcon(type) {
  const icons = {
    success: '&#10003;',
    error: '&#10007;',
    warning: '&#9888;',
    info: '&#8505;',
  };
  return icons[type] || icons.info;
}

// ==================
// Form Handling
// ==================

function initForms() {
  // Login form
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
  }

  // Register form
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.addEventListener('submit', handleRegister);
  }

  // Request form
  const requestForm = document.getElementById('request-form');
  if (requestForm) {
    requestForm.addEventListener('submit', handleRequest);
  }

  // Feedback form
  const feedbackForms = document.querySelectorAll('[data-feedback-form]');
  feedbackForms.forEach(form => {
    form.addEventListener('submit', handleFeedback);
  });

  // Review form
  const reviewForm = document.getElementById('review-form');
  if (reviewForm) {
    reviewForm.addEventListener('submit', handleReview);
  }

  // Character counters
  document.querySelectorAll('[data-maxlength]').forEach(input => {
    const maxLength = parseInt(input.dataset.maxlength);
    const counter = document.querySelector(`[data-counter-for="${input.id}"]`);

    if (counter) {
      const updateCounter = () => {
        const remaining = maxLength - input.value.length;
        counter.textContent = `${input.value.length}/${maxLength}`;
        counter.classList.toggle('text-error', remaining < 20);
      };

      input.addEventListener('input', updateCounter);
      updateCounter();
    }
  });
}

async function handleLogin(e) {
  e.preventDefault();
  const form = e.target;
  const email = form.querySelector('[name="email"]').value;
  const password = form.querySelector('[name="password"]').value;
  const submitBtn = form.querySelector('[type="submit"]');

  try {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Signing in...';

    await API.auth.login(email, password);
    showToast('Welcome back!', 'success');

    // Redirect to previous page or home
    const redirect = new URLSearchParams(window.location.search).get('redirect') || '/';
    window.location.href = redirect;
  } catch (error) {
    showToast(error.message || 'Login failed', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Sign In';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const form = e.target;
  const username = form.querySelector('[name="username"]').value;
  const email = form.querySelector('[name="email"]').value;
  const password = form.querySelector('[name="password"]').value;
  const confirmPassword = form.querySelector('[name="confirm-password"]').value;
  const submitBtn = form.querySelector('[type="submit"]');

  if (password !== confirmPassword) {
    showToast('Passwords do not match', 'error');
    return;
  }

  try {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating account...';

    await API.auth.register(username, email, password);
    showToast('Account created successfully!', 'success');
    window.location.href = '/profile';
  } catch (error) {
    showToast(error.message || 'Registration failed', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Create Account';
  }
}

async function handleRequest(e) {
  e.preventDefault();
  const form = e.target;
  const data = {
    title: form.querySelector('[name="title"]').value,
    description: form.querySelector('[name="description"]').value,
    category: form.querySelector('[name="category"]').value,
  };
  const submitBtn = form.querySelector('[type="submit"]');

  try {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    await API.requests.create(data);
    showToast('Request submitted successfully!', 'success');
    form.reset();

    // Refresh request list if on the same page
    if (typeof loadRequests === 'function') {
      loadRequests();
    }
  } catch (error) {
    showToast(error.message || 'Failed to submit request', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Submit Request';
  }
}

async function handleFeedback(e) {
  e.preventDefault();
  const form = e.target;
  const appId = form.dataset.appId;
  const data = {
    type: form.querySelector('[name="type"]').value,
    message: form.querySelector('[name="message"]').value,
  };
  const submitBtn = form.querySelector('[type="submit"]');

  try {
    submitBtn.disabled = true;
    await API.wildWest.submitFeedback(appId, data);
    showToast('Feedback submitted!', 'success');
    closeModal('feedback-modal');
    form.reset();
  } catch (error) {
    showToast(error.message || 'Failed to submit feedback', 'error');
  } finally {
    submitBtn.disabled = false;
  }
}

async function handleReview(e) {
  e.preventDefault();
  const form = e.target;
  const appId = form.dataset.appId;
  const data = {
    rating: parseInt(form.querySelector('[name="rating"]:checked')?.value || '5'),
    content: form.querySelector('[name="content"]').value,
  };
  const submitBtn = form.querySelector('[type="submit"]');

  try {
    submitBtn.disabled = true;
    await API.reviews.create(appId, data);
    showToast('Review submitted!', 'success');
    form.reset();

    // Refresh reviews if available
    if (typeof loadReviews === 'function') {
      loadReviews(appId);
    }
  } catch (error) {
    showToast(error.message || 'Failed to submit review', 'error');
  } finally {
    submitBtn.disabled = false;
  }
}

// ==================
// Copy to Clipboard
// ==================

function initCopyButtons() {
  document.querySelectorAll('[data-copy]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const target = document.querySelector(btn.dataset.copy);
      const text = target?.textContent || btn.dataset.copyText;

      if (text) {
        try {
          await navigator.clipboard.writeText(text);
          showToast('Copied to clipboard!', 'success');
        } catch (error) {
          // Fallback for older browsers
          const textarea = document.createElement('textarea');
          textarea.value = text;
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
          showToast('Copied to clipboard!', 'success');
        }
      }
    });
  });
}

// ==================
// Vote Buttons
// ==================

function initVoteButtons() {
  document.querySelectorAll('[data-vote]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const type = btn.dataset.vote;
      const appId = btn.dataset.appId;
      const requestId = btn.dataset.requestId;

      try {
        if (appId) {
          await API.wildWest.vote(appId, type);
        } else if (requestId) {
          if (btn.classList.contains('active')) {
            await API.requests.unvote(requestId);
          } else {
            await API.requests.vote(requestId);
          }
        }

        btn.classList.toggle('active');

        // Update vote count
        const countEl = btn.querySelector('.vote-count');
        if (countEl) {
          let count = parseInt(countEl.textContent);
          count += btn.classList.contains('active') ? 1 : -1;
          countEl.textContent = count;
        }
      } catch (error) {
        showToast(error.message || 'Vote failed', 'error');
      }
    });
  });
}

// ==================
// Lazy Loading
// ==================

function initLazyLoading() {
  if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          img.classList.remove('lazy');
          observer.unobserve(img);
        }
      });
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
      imageObserver.observe(img);
    });
  } else {
    // Fallback for older browsers
    document.querySelectorAll('img[data-src]').forEach(img => {
      img.src = img.dataset.src;
    });
  }
}

// ==================
// Authentication State
// ==================

function checkAuth() {
  const token = API.getToken();
  const authLinks = document.querySelectorAll('[data-auth]');
  const guestLinks = document.querySelectorAll('[data-guest]');

  authLinks.forEach(el => {
    el.style.display = token ? '' : 'none';
  });

  guestLinks.forEach(el => {
    el.style.display = token ? 'none' : '';
  });

  // Load user info if logged in
  if (token) {
    loadCurrentUser();
  }
}

async function loadCurrentUser() {
  try {
    const user = await API.auth.getCurrentUser();
    updateUserUI(user);
  } catch (error) {
    // Token might be invalid
    API.removeToken();
    checkAuth();
  }
}

function updateUserUI(user) {
  const userNameEls = document.querySelectorAll('[data-user-name]');
  const userAvatarEls = document.querySelectorAll('[data-user-avatar]');
  const userTierEls = document.querySelectorAll('[data-user-tier]');

  userNameEls.forEach(el => {
    el.textContent = user.username;
  });

  userAvatarEls.forEach(el => {
    el.textContent = user.username[0].toUpperCase();
  });

  userTierEls.forEach(el => {
    el.textContent = user.tier;
    el.className = `profile-tier tier-${user.tier.toLowerCase()}`;
  });
}

// ==================
// Utility Functions
// ==================

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatNumber(num) {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
}

function getUrlParam(param) {
  return new URLSearchParams(window.location.search).get(param);
}

function setUrlParam(param, value) {
  const url = new URL(window.location);
  if (value) {
    url.searchParams.set(param, value);
  } else {
    url.searchParams.delete(param);
  }
  window.history.pushState({}, '', url);
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function throttle(func, limit) {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// ==================
// Page-specific Loaders
// ==================

// These functions can be called from individual pages

async function loadFeaturedApps(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  try {
    const data = await API.apps.getFeatured();
    container.innerHTML = data.apps.map(app => renderFeaturedCard(app)).join('');
    initCarousel();
  } catch (error) {
    container.innerHTML = '<p class="text-muted">Failed to load featured apps</p>';
  }
}

async function loadPopularApps(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  try {
    const data = await API.apps.getPopular();
    container.innerHTML = data.apps.map(app => renderAppCard(app)).join('');
  } catch (error) {
    container.innerHTML = '<p class="text-muted">Failed to load popular apps</p>';
  }
}

async function loadLatestApps(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  try {
    const data = await API.apps.getLatest();
    container.innerHTML = data.apps.map(app => renderAppCard(app)).join('');
  } catch (error) {
    container.innerHTML = '<p class="text-muted">Failed to load latest apps</p>';
  }
}

async function loadCategories(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  try {
    const data = await API.categories.getAll();
    const categories = data.categories || data;

    if (Array.isArray(categories) && categories.length > 0) {
      container.innerHTML = categories.map(cat => {
        // Handle both string categories and object categories
        if (typeof cat === 'string') {
          return renderCategoryCard({ name: cat, slug: cat.toLowerCase(), count: null });
        }
        return renderCategoryCard(cat);
      }).join('');
    } else {
      container.innerHTML = '<p class="text-muted">No categories available</p>';
    }
  } catch (error) {
    container.innerHTML = '<p class="text-muted">Failed to load categories</p>';
  }
}

// ==================
// Render Functions
// ==================

function renderAppCard(app) {
  return `
    <a href="/app/${app.slug}" class="card app-card">
      <div class="app-card-image">
        ${app.screenshot
          ? `<img src="${app.screenshot}" alt="${escapeHtml(app.name)} screenshot" loading="lazy">`
          : `<div class="app-card-icon">${app.icon || app.name[0]}</div>`
        }
      </div>
      <div class="app-card-content">
        <h3 class="app-card-title">${escapeHtml(app.name)}</h3>
        <p class="app-card-desc">${escapeHtml(app.description || '')}</p>
        <div class="app-card-meta">
          <div class="app-card-rating">
            <span>&#9733;</span>
            <span>${app.average_rating?.toFixed(1) || 'N/A'}</span>
          </div>
          <span class="app-card-downloads">${formatNumber(app.download_count || 0)} downloads</span>
          <span class="app-card-category">${escapeHtml(app.category || 'App')}</span>
        </div>
      </div>
    </a>
  `;
}

function renderFeaturedCard(app) {
  return `
    <div class="carousel-slide">
      <div class="featured-card">
        <div class="featured-content">
          <span class="featured-badge">&#9733; Featured</span>
          <h2 class="featured-title">${escapeHtml(app.name)}</h2>
          <p class="featured-desc">${escapeHtml(app.description || '')}</p>
          <a href="/app/${app.slug}" class="btn btn-primary">View App</a>
        </div>
        <div class="featured-image">
          ${app.screenshot
            ? `<img src="${app.screenshot}" alt="${escapeHtml(app.name)}">`
            : `<div class="app-card-icon" style="font-size:4rem;">${app.icon || app.name[0]}</div>`
          }
        </div>
      </div>
    </div>
  `;
}

function renderCategoryCard(category) {
  const name = category.name || category;
  const slug = category.slug || (typeof name === 'string' ? name.toLowerCase() : '');
  const displayName = typeof name === 'string' ? name.charAt(0).toUpperCase() + name.slice(1).replace(/-/g, ' ') : name;
  const count = category.count;

  return `
    <a href="/browse?category=${encodeURIComponent(slug)}" class="card category-card">
      <div class="category-icon">${displayName.charAt(0).toUpperCase()}</div>
      <span class="category-name">${escapeHtml(displayName)}</span>
      ${count !== null && count !== undefined ? `<span class="category-count">${count} apps</span>` : ''}
    </a>
  `;
}

function renderRequestCard(request) {
  return `
    <div class="request-card">
      <div class="request-votes">
        <button class="request-vote-btn ${request.voted ? 'active' : ''}"
                data-vote="up" data-request-id="${request.id}" aria-label="Upvote">
          &#9650;
        </button>
        <span class="request-vote-count">${request.votes}</span>
      </div>
      <div class="request-content">
        <h3>${escapeHtml(request.title)}</h3>
        <p>${escapeHtml(request.description)}</p>
        <div class="request-meta">
          <span>by ${escapeHtml(request.author)}</span>
          <span>${formatDate(request.createdAt)}</span>
        </div>
      </div>
      <span class="request-status status-${request.status}">${request.status}</span>
    </div>
  `;
}

function renderReviewCard(review) {
  return `
    <div class="review-card">
      <div class="review-header">
        <div class="review-avatar">${review.author[0].toUpperCase()}</div>
        <div class="review-meta">
          <span class="review-author">${escapeHtml(review.author)}</span>
          <span class="review-date">${formatDate(review.createdAt)}</span>
        </div>
        <div class="review-rating">${'&#9733;'.repeat(review.rating)}${'&#9734;'.repeat(5 - review.rating)}</div>
      </div>
      <p class="review-content">${escapeHtml(review.content)}</p>
    </div>
  `;
}

// Make functions globally available
window.showToast = showToast;
window.openModal = openModal;
window.closeModal = closeModal;
window.loadFeaturedApps = loadFeaturedApps;
window.loadPopularApps = loadPopularApps;
window.loadLatestApps = loadLatestApps;
window.loadCategories = loadCategories;
window.renderAppCard = renderAppCard;
window.renderRequestCard = renderRequestCard;
window.renderReviewCard = renderReviewCard;
window.formatDate = formatDate;
window.formatNumber = formatNumber;
window.getUrlParam = getUrlParam;
window.setUrlParam = setUrlParam;
window.escapeHtml = escapeHtml;
