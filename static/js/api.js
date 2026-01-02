/**
 * Flick Store API Client
 * Handles all API communication with the backend
 */

const API = {
  // Base URL - update for production
  baseUrl: '/api',

  // Default request options
  defaultOptions: {
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'same-origin',
  },

  /**
   * Make an API request
   * @param {string} endpoint - API endpoint
   * @param {Object} options - Fetch options
   * @returns {Promise<Object>} Response data
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      ...this.defaultOptions,
      ...options,
      headers: {
        ...this.defaultOptions.headers,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      // Handle non-JSON responses
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return { success: true };
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || `HTTP error! status: ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  },

  /**
   * GET request
   */
  get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    return this.request(url, { method: 'GET' });
  },

  /**
   * POST request
   */
  post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * PUT request
   */
  put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * DELETE request
   */
  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  },

  // ==================
  // Auth Endpoints (session-based)
  // ==================

  auth: {
    async login(username, password) {
      // Session-based auth - cookie is set automatically
      return API.post('/auth/login', { username, password });
    },

    async register(username, email, password) {
      // Session-based auth - cookie is set automatically
      return API.post('/auth/register', { username, email, password });
    },

    async logout() {
      return API.post('/auth/logout');
    },

    async getCurrentUser() {
      return API.get('/auth/me');
    },

    async updateProfile(data) {
      return API.put('/auth/profile', data);
    },

    async changePassword(currentPassword, newPassword) {
      return API.post('/auth/change-password', { currentPassword, newPassword });
    },
  },

  // ==================
  // Apps Endpoints
  // ==================

  apps: {
    async getAll(params = {}) {
      return API.get('/apps', params);
    },

    async getFeatured() {
      return API.get('/apps/featured');
    },

    async getPopular(limit = 10) {
      return API.get('/apps/popular', { limit });
    },

    async getLatest(limit = 10) {
      return API.get('/apps/latest', { limit });
    },

    async getById(id) {
      return API.get(`/apps/${id}`);
    },

    async getBySlug(slug) {
      return API.get(`/apps/slug/${slug}`);
    },

    async search(query, params = {}) {
      return API.get('/apps/search', { q: query, ...params });
    },

    async getByCategory(category, params = {}) {
      return API.get(`/apps/category/${category}`, params);
    },

    async getScreenshots(appId) {
      return API.get(`/apps/${appId}/screenshots`);
    },

    async getVersions(appId) {
      return API.get(`/apps/${appId}/versions`);
    },

    async download(appId) {
      return API.post(`/apps/${appId}/download`);
    },

    async reportIssue(appId, data) {
      return API.post(`/apps/${appId}/report`, data);
    },
  },

  // ==================
  // Categories Endpoints
  // ==================

  categories: {
    async getAll() {
      return API.get('/apps/categories');
    },
  },

  // ==================
  // Reviews Endpoints
  // ==================

  reviews: {
    async getByApp(appId, params = {}) {
      return API.get(`/apps/${appId}/reviews`, params);
    },

    async create(appId, data) {
      return API.post(`/apps/${appId}/reviews`, data);
    },

    async update(reviewId, data) {
      return API.put(`/reviews/${reviewId}`, data);
    },

    async delete(reviewId) {
      return API.delete(`/reviews/${reviewId}`);
    },

    async markHelpful(reviewId) {
      return API.post(`/reviews/${reviewId}/helpful`);
    },
  },

  // ==================
  // Wild West Endpoints
  // ==================

  wildWest: {
    async getAll(params = {}) {
      return API.get('/wild-west', params);
    },

    async getById(id) {
      return API.get(`/wild-west/${id}`);
    },

    async vote(appId, type) {
      return API.post(`/wild-west/${appId}/vote`, { type }); // 'up' or 'down'
    },

    async submitFeedback(appId, data) {
      return API.post(`/wild-west/${appId}/feedback`, data);
    },
  },

  // ==================
  // Requests Endpoints
  // ==================

  requests: {
    async getAll(params = {}) {
      return API.get('/requests', params);
    },

    async getById(id) {
      return API.get(`/requests/${id}`);
    },

    async create(data) {
      return API.post('/requests', data);
    },

    async vote(requestId) {
      return API.post(`/requests/${requestId}/vote`);
    },

    async unvote(requestId) {
      return API.delete(`/requests/${requestId}/vote`);
    },

    async getMyRequests() {
      return API.get('/requests/mine');
    },
  },

  // ==================
  // Admin Endpoints
  // ==================

  admin: {
    async getStats() {
      return API.get('/admin/stats');
    },

    async getPendingRequests() {
      return API.get('/admin/requests/pending');
    },

    async approveRequest(requestId) {
      return API.post(`/admin/requests/${requestId}/approve`);
    },

    async rejectRequest(requestId, reason) {
      return API.post(`/admin/requests/${requestId}/reject`, { reason });
    },

    async getWildWestApps() {
      return API.get('/admin/wild-west');
    },

    async promoteToStable(appId) {
      return API.post(`/admin/wild-west/${appId}/promote`);
    },

    async getUsers(params = {}) {
      return API.get('/admin/users', params);
    },

    async updateUserTier(userId, tier) {
      return API.put(`/admin/users/${userId}/tier`, { tier });
    },

    async getReports(params = {}) {
      return API.get('/admin/reports', params);
    },

    async resolveReport(reportId, action) {
      return API.post(`/admin/reports/${reportId}/resolve`, { action });
    },
  },
};

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = API;
}
