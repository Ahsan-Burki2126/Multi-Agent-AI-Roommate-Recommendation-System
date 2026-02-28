/**
 * Authentication Module
 * Handles login, registration, and auth state management
 */

class AuthManager {
  constructor() {
    this.currentUser = this.loadUser();
    this.initializeAuth();
  }

  /**
   * Initialize authentication on page load
   */
  initializeAuth() {
    const token = localStorage.getItem("token");

    if (token && !this.currentUser) {
      // Token exists but user not loaded, try to verify
      this.verifyToken();
    }

    // Update UI based on auth state
    this.updateAuthUI();
  }

  /**
   * Register new user
   */
  async register(email, password, passwordConfirm, fullName, city, gender) {
    // Validation
    if (!email || !password || !passwordConfirm || !fullName) {
      throw new Error("Please fill in all required fields");
    }

    if (password !== passwordConfirm) {
      throw new Error("Passwords do not match");
    }

    if (password.length < 6) {
      throw new Error("Password must be at least 6 characters");
    }

    if (!this.isValidEmail(email)) {
      throw new Error("Invalid email format");
    }

    // Call API
    const response = await api.register(
      email,
      password,
      fullName,
      city,
      gender,
    );

    if (response.user_id) {
      // Registration successful, show message
      return {
        success: true,
        message: "Registration successful! Please log in.",
        user_id: response.user_id,
      };
    }

    throw new Error(response.error || "Registration failed");
  }

  /**
   * Login user
   */
  async login(email, password) {
    if (!email || !password) {
      throw new Error("Email and password required");
    }

    const response = await api.login(email, password);

    if (response.access_token) {
      // Save user info
      this.currentUser = {
        user_id: response.user_id,
        email: response.email,
        full_name: response.full_name,
      };
      localStorage.setItem("user", JSON.stringify(this.currentUser));
      api.setToken(response.access_token);

      return {
        success: true,
        user: this.currentUser,
      };
    }

    throw new Error(response.error || "Login failed");
  }

  /**
   * Logout user
   */
  async logout() {
    try {
      await api.logout();
    } catch (error) {
      console.warn("Logout API call failed:", error);
    }

    // Clear local state
    this.currentUser = null;
    localStorage.removeItem("user");
    api.clearToken();
    this.updateAuthUI();

    // Redirect to login
    window.location.href = "/login.html";
  }

  /**
   * Verify token is still valid
   */
  async verifyToken() {
    try {
      const response = await api.verify();
      if (response.valid) {
        return true;
      }
    } catch (error) {
      console.warn("Token verification failed:", error);
      api.clearToken();
    }

    return false;
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    return !!this.currentUser && api.isAuthenticated();
  }

  /**
   * Get current user
   */
  getCurrentUser() {
    return this.currentUser;
  }

  /**
   * Get user ID
   */
  getUserId() {
    return this.currentUser?.user_id;
  }

  /**
   * Load user from localStorage
   */
  loadUser() {
    const userStr = localStorage.getItem("user");
    return userStr ? JSON.parse(userStr) : null;
  }

  /**
   * Validate email format
   */
  isValidEmail(email) {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return pattern.test(email);
  }

  /**
   * Update navbar/menu based on auth state
   */
  updateAuthUI() {
    const authMenu = document.getElementById("auth-menu");
    const userMenu = document.getElementById("user-menu");

    if (!authMenu || !userMenu) {
      return; // Elements not on this page
    }

    if (this.isAuthenticated()) {
      // Hide login/register, show user menu
      authMenu.style.display = "none";
      userMenu.style.display = "flex";

      // Update user name
      const userNameEl = document.getElementById("user-name");
      if (userNameEl) {
        userNameEl.textContent = this.currentUser.full_name;
      }
    } else {
      // Show login/register, hide user menu
      authMenu.style.display = "flex";
      userMenu.style.display = "none";
    }
  }

  /**
   * Redirect to login if not authenticated
   */
  requireAuth() {
    if (!this.isAuthenticated()) {
      window.location.href = "/login.html";
    }
  }
}

// Create global auth manager
const auth = new AuthManager();

// Check auth on page load
document.addEventListener("DOMContentLoaded", () => {
  auth.updateAuthUI();
});
