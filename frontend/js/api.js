/**
 * API Client
 * Handles all communication with the Flask backend API
 *
 * Configuration: Update BASE_URL if backend is on different host/port
 */

// In production (Vercel), API routes are on the same domain (routed via vercel.json).
// In local development, the backend runs separately on port 5000.
const BASE_URL = (
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1"
)
  ? "http://localhost:5000"
  : "";   // same origin on Vercel — routes handled by vercel.json

class APIClient {
  constructor() {
    this.baseUrl = BASE_URL;
  }

  /**
   * Get current token from localStorage (always fresh)
   */
  getToken() {
    return localStorage.getItem("token");
  }

  /**
   * Make HTTP request to the API
   *
   * @param {string} method - HTTP method (GET, POST, PUT, DELETE)
   * @param {string} endpoint - API endpoint (without base URL)
   * @param {object} data - Request body (optional)
   * @returns {Promise} - Response data
   */
  async request(method, endpoint, data = null) {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getToken();
    const options = {
      method: method,
      headers: {
        "Content-Type": "application/json",
      },
    };

    // Debug logging
    console.log("API Request:", method, endpoint);
    console.log("Token present:", !!token);
    console.log(
      "Token value (first 50 chars):",
      token ? token.substring(0, 50) + "..." : "NULL",
    );

    // Add token if available
    if (token) {
      options.headers["Authorization"] = `Bearer ${token}`;
    }

    // Add body for non-GET requests
    if (data && method !== "GET") {
      options.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url, options);

      // Handle 401 (unauthorized) - clear token and redirect to login
      // But don't redirect if we're already on the login page (wrong credentials case)
      if (response.status === 401 && !window.location.pathname.includes("login")) {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        window.location.href = "/login.html";
        return;
      }

      if (!response.ok) {
        let errorMsg = `API error: ${response.status}`;
        try {
          const error = await response.json();
          errorMsg = error.error || error.message || errorMsg;
        } catch {
          // Response was not JSON (e.g. Vercel HTML error page)
          const text = await response.text().catch(() => "");
          if (text) errorMsg = text.substring(0, 150);
        }
        throw new Error(errorMsg);
      }

      return await response.json();
    } catch (error) {
      console.error("API error:", error);
      throw error;
    }
  }

  /**
   * Authentication Endpoints
   */

  // Register new user
  async register(email, password, fullName, city, gender, age) {
    return this.request("POST", "/auth/register", {
      email,
      password,
      full_name: fullName,
      city,
      gender,
      age,
    });
  }

  // Login user
  async login(email, password) {
    const response = await this.request("POST", "/auth/login", {
      email,
      password,
    });

    // Store token in localStorage (getToken() will read it)
    if (response.access_token) {
      localStorage.setItem("token", response.access_token);
    }

    return response;
  }

  // Verify current user
  async verify() {
    return this.request("GET", "/auth/verify");
  }

  // Logout
  async logout() {
    return this.request("POST", "/auth/logout");
  }

  // Change password
  async changePassword(currentPassword, newPassword) {
    return this.request("POST", "/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  /**
   * User Endpoints
   */

  // Get user profile
  async getUser(userId) {
    return this.request("GET", `/users/${userId}`);
  }

  // Get current user profile with preferences
  async getUserProfile(userId) {
    return this.request("GET", `/users/${userId}/profile`);
  }

  // Update user profile
  async updateUser(userId, data) {
    return this.request("PUT", `/users/${userId}`, data);
  }

  // Search users
  async searchUsers(params) {
    const queryString = new URLSearchParams(params).toString();
    return this.request("GET", `/users/search?${queryString}`);
  }

  // Deactivate user account
  async deactivateUser(userId) {
    return this.request("DELETE", `/users/${userId}`);
  }

  // Delete user account (alias for deactivateUser)
  async deleteUser(userId) {
    return this.deactivateUser(userId);
  }

  /**
   * Preference Endpoints
   */

  // Get user preferences
  async getPreferences(userId) {
    return this.request("GET", `/preferences/user/${userId}`);
  }

  // Create/update preferences
  async setPreferences(userId, preferences) {
    return this.request("POST", `/preferences/user/${userId}`, preferences);
  }

  // Update preferences
  async updatePreferences(userId, preferences) {
    return this.request("PUT", `/preferences/user/${userId}`, preferences);
  }

  // Get preference vector
  async getPreferenceVector(userId) {
    return this.request("GET", `/preferences/${userId}/vector`);
  }

  // Vectorize preferences (trigger Analysis Agent)
  async vectorizePreferences(userId) {
    return this.request("POST", `/preferences/${userId}/vectorize`);
  }

  /**
   * Room Endpoints
   */

  // Get all rooms
  async getRooms(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request("GET", `/rooms?${queryString}`);
  }

  // Get single room
  async getRoom(roomId) {
    return this.request("GET", `/rooms/${roomId}`);
  }

  // Create room listing
  async createRoom(roomData) {
    return this.request("POST", "/rooms", roomData);
  }

  // Update room
  async updateRoom(roomId, roomData) {
    return this.request("PUT", `/rooms/${roomId}`, roomData);
  }

  // Delete room
  async deleteRoom(roomId) {
    return this.request("DELETE", `/rooms/${roomId}`);
  }

  // Search rooms
  async searchRooms(params) {
    const queryString = new URLSearchParams(params).toString();
    return this.request("GET", `/rooms/search?${queryString}`);
  }

  // Get user's rooms
  async getUserRooms(userId) {
    return this.request("GET", `/rooms/user/${userId}`);
  }

  /**
   * Matching Endpoints
   */

  // Compute matches for user
  async computeMatches(params = {}) {
    return this.request("POST", "/matches/compute", params);
  }

  // Get user's matches
  async getUserMatches(userId, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request("GET", `/matches/user/${userId}?${queryString}`);
  }

  // Score two users
  async scoreUsers(userAId, userBId) {
    return this.request("POST", `/matches/${userAId}/${userBId}`);
  }

  // Delete score
  async deleteScore(scoreId) {
    return this.request("DELETE", `/matches/${scoreId}`);
  }

  // Check conflicts
  async checkConflicts(userAId, userBId) {
    return this.request("GET", `/matches/conflicts/${userAId}/${userBId}`);
  }

  /**
   * Recommendation Endpoints
   */

  // Get recommendations
  async getRecommendations(userId, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(
      "GET",
      `/recommendations/user/${userId}?${queryString}`,
    );
  }

  // Get new recommendations
  async getNewRecommendations(userId, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(
      "GET",
      `/recommendations/user/${userId}/new?${queryString}`,
    );
  }

  // Get single recommendation
  async getRecommendation(recId) {
    return this.request("GET", `/recommendations/${recId}`);
  }

  // Mark viewed
  async markViewed(recId) {
    return this.request("PUT", `/recommendations/${recId}/viewed`);
  }

  // Mark liked
  async markLiked(recId) {
    return this.request("PUT", `/recommendations/${recId}/liked`);
  }

  // Mark disliked
  async markDisliked(recId) {
    return this.request("PUT", `/recommendations/${recId}/disliked`);
  }

  // Delete recommendation
  async deleteRecommendation(recId) {
    return this.request("DELETE", `/recommendations/${recId}`);
  }

  // Get stats
  async getRecommendationStats(userId) {
    return this.request("GET", `/recommendations/user/${userId}/stats`);
  }

  // Get mutual matches (FR-6.1)
  async getMutualMatches(userId) {
    return this.request("GET", `/recommendations/user/${userId}/mutual`);
  }

  /**
   * Orchestration Endpoints (Agent Pipeline)
   */

  // Execute matching pipeline
  async findMatches(params = {}) {
    return this.request("POST", "/orchestrate/matches", params);
  }

  // Execute room search pipeline
  async findRooms(params = {}) {
    return this.request("POST", "/orchestrate/rooms", params);
  }

  // Get system status
  async getSystemStatus() {
    return this.request("GET", "/orchestrate/status");
  }

  // Get execution log
  async getExecutionLog(limit = 50) {
    return this.request("GET", `/orchestrate/execution-log?limit=${limit}`);
  }

  // Get pipeline info
  async getPipelineInfo() {
    return this.request("GET", "/orchestrate/pipeline-info");
  }

  /**
   * Utility Methods
   */

  // Set token (for manual token setting)
  setToken(token) {
    localStorage.setItem("token", token);
  }

  // Clear token
  clearToken() {
    localStorage.removeItem("token");
  }

  // Check if user is authenticated
  isAuthenticated() {
    return !!this.getToken();
  }
}

// Create global API client instance
const api = new APIClient();
