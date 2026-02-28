# RoomMate Finder - Frontend

A modern, responsive web application for finding compatible roommates using AI-powered matching.

## 📁 Project Structure

```
frontend/
├── index.html              # Landing page
├── register.html           # User registration
├── login.html              # User login
├── dashboard.html          # Main user hub
├── preferences.html        # Preference setup wizard
├── matches.html            # Roommate recommendations
├── rooms.html              # Room search and browse
├── profile.html            # User profile management
├── settings.html           # Account settings
├── css/
│   └── style.css          # Main stylesheet (850+ lines)
└── js/
    ├── api.js              # REST API client (400+ lines)
    ├── auth.js             # Authentication manager (180+ lines)
    └── main.js             # UI utilities and helpers (600+ lines)
```

## 🚀 Getting Started

### Prerequisites
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Backend API running at `http://localhost:5000`

### Setup

1. **Serve the Frontend**
   ```bash
   # Using Python's built-in server
   python -m http.server 8000
   
   # Or using Node.js
   npm install -g http-server
   http-server
   ```

2. **Access the Application**
   - Open `http://localhost:8000` in your browser
   - You'll see the landing page with options to register or login

### Configuration

Edit `frontend/js/api.js` to change the API base URL:

```javascript
// Line 2 in api.js
BASE_URL = 'http://localhost:5000'  // Change this if needed
```

## 📄 Pages Overview

### 1. **index.html** - Landing Page
- Hero section with call-to-action
- Features showcase
- How it works steps
- CTA section
- Footer with links
- **Auth State**: Shows different CTAs based on login status

### 2. **register.html** - User Registration
- Email, password, full name fields
- City and gender selection
- Client-side form validation
- Terms agreement checkbox
- Link to login page
- **Validation**: Email, password (min 6 chars), password match

### 3. **login.html** - User Login
- Email and password fields
- "Remember me" checkbox
- Redirect to dashboard on success
- Link to register page
- **Error Handling**: Shows specific error messages

### 4. **dashboard.html** - Main User Hub
- Welcome message with user name
- Profile completion indicator
- Statistics cards:
  - Profile completion %
  - Recommendations count
  - Liked count
  - Rooms saved count
- Quick action cards:
  - Edit profile
  - Set preferences
  - View matches
  - Browse rooms
- Recent recommendations preview
- Getting started guide
- **Protected**: Requires authentication

### 5. **preferences.html** - Multi-Step Wizard
- 5-step wizard with progress indicator:
  - Step 1: Budget (min/max, location)
  - Step 2: Age range (min/max)
  - Step 3: Lifestyle (noise, smoking, pets, schedule)
  - Step 4: Cleanliness level
  - Step 5: Review summary
- Form validation at each step
- Next/Previous navigation
- Save preferences and vectorize
- **Protected**: Requires authentication

### 6. **matches.html** - Roommate Recommendations
- List of AI-generated recommendations
- Match cards with:
  - User name and location
  - Compatibility score (%)
  - Match strength label
  - Explanation with details
  - Like/Dislike buttons
- Filters:
  - Minimum score (50%, 60%, 70%, 80%, 90%)
  - Sort by score (high/low) or newest
- Pagination with 6 items per page
- "Find new matches" button
- **Protected**: Requires authentication

### 7. **rooms.html** - Room Search
- Comprehensive search filters:
  - Location (text search)
  - Price range (min/max)
  - Room type (single, double, studio, private)
  - Furnishing (furnished, unfurnished, partial)
  - Bed size (single, double, queen, king)
  - Pets allowed
  - Smoking allowed
- Room cards with:
  - Title, price (/month)
  - Location, bed size, furnishing
  - Amenities badges
  - Description
  - View details and contact buttons
- Pagination with 6 items per page
- Reset filters button
- **Protected**: Requires authentication

### 8. **profile.html** - User Profile Management
- Profile sidebar with:
  - Avatar with initials
  - Profile completion percentage
  - Change avatar button
- Profile form with fields:
  - Email (read-only)
  - Full name
  - Bio/About
  - City
  - Gender
  - Phone (optional)
  - Occupation (optional)
  - Age (optional)
- Save/Cancel buttons
- Danger zone with delete account option
- **Protected**: Requires authentication

### 9. **settings.html** - Account Settings
- Change password section
- Email notification preferences
- Privacy settings (profile visibility, online status)
- Account information display
- Download data button
- Logout all devices button
- Delete account section
- **Protected**: Requires authentication

## 🔐 Authentication Flow

### Registration
1. User fills signup form
2. Client validates locally
3. API call to `/auth/register`
4. Token stored in localStorage
5. Redirect to dashboard

### Login
1. User enters credentials
2. Client validates
3. API call to `/auth/login`
4. Token + user data stored in localStorage
5. Redirect to dashboard

### Session Management
- JWT token stored in localStorage
- Auto-added to all API requests
- 401 errors redirect to login
- `auth.requireAuth()` protects pages

## 📦 JavaScript Modules

### `api.js` (400+ lines)
**APIClient Class**
- Centralized REST API communication
- Auto JWT token handling
- Error handling with 401 redirects
- Methods for all 42 backend endpoints

**Methods by Category:**
- **Auth**: register, login, logout, verify
- **Users**: getUser, updateUser, searchUsers, deactivateUser
- **Preferences**: getPreferences, setPreferences, vectorizePreferences
- **Rooms**: getRooms, createRoom, updateRoom, deleteRoom, searchRooms
- **Matching**: computeMatches, getUserMatches, scoreUsers, checkConflicts
- **Recommendations**: getRecommendations, markViewed, markLiked, markDisliked
- **Orchestration**: findMatches, findRooms, getSystemStatus, getExecutionLog

**Usage:**
```javascript
// In any HTML page
<script src="js/api.js"></script>

// Use global api instance
const matches = await api.findMatches({min_score: 70});
const user = await api.getUser(userId);
```

### `auth.js` (180+ lines)
**AuthManager Class**
- Complete authentication lifecycle
- localStorage persistence
- User state management
- Form validation

**Methods:**
- `register(email, password, passwordConfirm, fullName, city, gender)`
- `login(email, password)`
- `logout()`
- `isAuthenticated()` → boolean
- `getCurrentUser()` → user object
- `requireAuth()` → redirect if not logged in

**Usage:**
```javascript
// Check authentication
if (auth.isAuthenticated()) {
    const user = auth.getCurrentUser();
}

// Protect pages
auth.requireAuth();  // Redirects to login if not authenticated
```

### `main.js` (600+ lines)
**Utility Functions**

**Alerts:**
- `showAlert(message, type)` - Generic alert
- `showSuccess(message)`, `showError(message)`, `showWarning(message)`

**Loading States:**
- `setLoading(element, isLoading)` - Toggle loading state
- `showLoader(containerId)` - Show spinner

**Forms:**
- `getFormData(formElement)` - Get form as object
- `setFormData(formElement, data)` - Populate form from object
- `clearForm(formElement)` - Reset form
- `showFormError(form, field, message)` - Show field error
- `clearFormErrors(formElement)` - Clear all errors

**Formatting:**
- `formatCurrency(amount)` - $1,234.56
- `formatDate(dateString)` - Jan 1, 2024
- `formatDateTime(dateString)` - Jan 1, 2024 12:34 PM
- `getRelativeTime(dateString)` - "2h ago"

**Match Display:**
- `getMatchStrengthLabel(score)` - "Perfect Match", "Excellent", etc.
- `renderMatchCard(match, containerId)` - Render match card HTML
- `renderRoomCard(room, containerId)` - Render room card HTML

**Modals:**
- `showModal(title, content, options)` - Show modal dialog
- `closeModal(modal)` - Close modal
- `confirm(message)` → Promise<boolean> - Confirmation dialog

**Navigation:**
- `setActiveNav(linkId)` - Highlight active nav link

## 🎨 CSS System

### `style.css` (850+ lines)

**CSS Variables:**
```css
--primary-color: #2563eb;
--primary-dark: #1d4ed8;
--success-color: #10b981;
--danger-color: #ef4444;
--border-color: #e5e7eb;
--text-dark: #1f2937;
--text-light: #6b7280;
```

**Components:**
- **Navigation**: navbar, nav-menu, nav-link
- **Buttons**: btn-primary, btn-secondary, btn-success, btn-danger, btn-sm, btn-block
- **Forms**: input, select, textarea, checkbox, radio, form-group, form-error
- **Cards**: card, card-header, card-body, card-footer
- **Match Cards**: match-card, match-avatar, match-explanation, match-strength
- **Alerts**: alert-success, alert-error, alert-warning, alert-info
- **Grid**: grid-cols-1, grid-cols-2, grid-cols-3
- **Utilities**: mt-*, mb-*, text-*, font-*

**Responsive Breakpoints:**
- 768px: Tablet
- 480px: Mobile

## 🔄 API Integration

All pages communicate with the backend via REST API and the APIClient:

```javascript
// Example: Load recommendations
const recommendations = await api.getRecommendations({limit: 50});

// Example: Save preferences
await api.setPreferences({
    min_budget: 500,
    max_budget: 2000,
    min_age: 20,
    max_age: 35,
    noise_tolerance: 3,
    smoking_preference: 'no',
    pets_preference: 'any'
});

// Example: Find matches
const matches = await api.findMatches({
    min_score: 70,
    limit: 100
});

// Example: Error handling
try {
    await api.request('GET', '/protected-endpoint');
} catch (error) {
    if (error.status === 401) {
        // Auth redirect handled automatically
    }
}
```

## 🛠️ Development

### Adding a New Page

1. Create HTML file in `frontend/`
2. Import CSS and JS:
   ```html
   <link rel="stylesheet" href="css/style.css">
   <script src="js/api.js"></script>
   <script src="js/auth.js"></script>
   <script src="js/main.js"></script>
   ```
3. Protect with auth if needed:
   ```javascript
   auth.requireAuth();
   ```
4. Add navigation link in navbar
5. Use `api` and `auth` globals

### Common Patterns

**Protected Page:**
```html
<script>
    auth.requireAuth();  // Redirects if not logged in
</script>
```

**Load Data:**
```javascript
async function loadData() {
    try {
        const data = await api.endpoint();
        // Display data
    } catch (error) {
        showError(error.message);
    }
}

document.addEventListener('DOMContentLoaded', loadData);
```

**Form Submission:**
```javascript
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormErrors(form);
    
    // Validate
    if (!field) {
        showFormError(form, fieldName, 'Error message');
        return;
    }
    
    // Submit
    const btn = form.querySelector('button[type="submit"]');
    setLoading(btn, true);
    
    try {
        await api.method(data);
        showSuccess('Success!');
    } catch (error) {
        setLoading(btn, false);
        showError(error.message);
    }
});
```

## 📱 Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## 🚧 Future Enhancements

- [ ] Real-time notifications (WebSocket)
- [ ] User messaging system
- [ ] Photo uploads and gallery
- [ ] Advanced search filters
- [ ] Chat interface
- [ ] Mobile app (React Native)
- [ ] PWA features (offline mode)
- [ ] Dark mode toggle

## 📄 License

MIT License - See LICENSE file for details

## 👥 Support

For issues or questions, please contact the development team or open an issue in the repository.

---

**Last Updated:** February 25, 2024
**Version:** 1.0.0 - Phase 5 Complete
