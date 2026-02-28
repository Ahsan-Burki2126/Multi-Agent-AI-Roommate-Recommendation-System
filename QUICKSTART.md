# Quick Start Guide - RoomMate Finder

Get the RoomMate Finder application up and running in 5 minutes!

---

## 📋 Prerequisites

- **Python 3.8+** (for backend)
- **Modern Web Browser** (Chrome, Firefox, Safari, Edge)
- **Git** (to clone the repository)

---

## 🚀 Quickstart (Backend + Frontend)

### Step 1: Clone & Setup Backend

```bash
# Clone repository (if not already done)
git clone <repository-url>
cd roommate-matching-system/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create database
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### Step 2: Start Backend Server

```bash
# Make sure venv is activated
python app.py

# You should see:
# * Running on http://127.0.0.1:5000
```

✅ Backend is now running on `http://localhost:5000`

### Step 3: Start Frontend Server

**In a NEW terminal window/tab:**

```bash
cd roommate-matching-system/frontend

# Option 1: Using Python
python -m http.server 8000

# Option 2: Using Node.js (if installed)
npx http-server

# You should see:
# Serving HTTP on 0.0.0.0 port 8000
```

✅ Frontend is now running on `http://localhost:8000`

### Step 4: Open Application

1. Open your browser
2. Go to `http://localhost:8000`
3. You're ready to use the app!

---

## 👤 Test Account (Example)

### Register a New Account
1. Click "Get Started Free"
2. Fill in the registration form:
   - Email: `test@example.com`
   - Password: `password123`
   - Full Name: `Test User`
   - City: `New York`
   - Gender: `Male/Female`
3. Click "Create Account"
4. You're logged in!

---

## 📱 Using the Application

### First Time User Flow

1. **Dashboard** - See your profile completion and quick stats
2. **Set Preferences** - Configure your roommate preferences (5-step wizard)
3. **View Matches** - See AI-generated recommendations with scores
4. **Browse Rooms** - Search for available rooms with filters
5. **Edit Profile** - Add more details to improve matches
6. **Settings** - Manage your account

### Key Pages
- `/` - Landing page
- `/register.html` - Create account
- `/login.html` - Sign in
- `/dashboard.html` - Main hub
- `/preferences.html` - Preference setup
- `/matches.html` - View recommendations
- `/rooms.html` - Browse rooms
- `/profile.html` - User profile
- `/settings.html` - Account settings

---

## 🔧 Configuration

### Change API Base URL (if not localhost)

Edit `frontend/js/api.js`:

```javascript
// Line 2 - Change this to your API URL
const BASE_URL = 'http://localhost:5000';  // Change if needed
```

### Change Backend Port

Edit `backend/app.py`:

```python
# Line at bottom
if __name__ == '__main__':
    app.run(debug=True, port=5000)  # Change port here
```

---

## 🐛 Troubleshooting

### "Connection Refused" Error
- Make sure backend is running on port 5000
- Check: `http://localhost:5000/api/health`

### Database Already Exists Error
- Backend created database automatically
- Database is at `backend/instance/roommate.db`

### Frontend Shows "Loading..." Forever
- Check browser console (F12) for errors
- Ensure backend is running
- Check API URL configuration

### Cannot Register / Login
- Make sure password is at least 6 characters
- Email must be valid format
- Check backend console for errors

### Port Already in Use
- Backend (5000): `lsof -i :5000` (macOS/Linux) or `netstat -ano | findstr :5000` (Windows)
- Frontend (8000): `lsof -i :8000` (macOS/Linux) or `netstat -ano | findstr :8000` (Windows)
- Kill process or change port number

---

## 📊 Test Data

### Sample User to Create
```
Email:    testuser@example.com
Password: password123
Name:     Test User
City:     San Francisco
Gender:   Male
```

### Sample Room Data
Rooms are managed through the admin API. Example:
```json
{
    "title": "Spacious Downtown Apartment",
    "location": "Downtown, San Francisco",
    "rent_price": 1200,
    "room_type": "Single Room",
    "bed_size": "Queen",
    "furnishing": "Furnished",
    "pets_allowed": true,
    "smoking_allowed": false,
    "amenities": "WiFi, Parking, Gym"
}
```

---

## 📖 Documentation

- **Backend Setup:** See `backend/README.md`
- **Frontend Setup:** See `frontend/README.md`
- **API Documentation:** See `API_SPECIFICATION.md`
- **Architecture:** See `ARCHITECTURE.md`
- **Project Status:** See `PROJECT_STATUS_FINAL.md`

---

## 🎯 Project Structure

```
roommate-matching-system/
├── backend/                # Flask backend
│   ├── app.py             # Main application
│   ├── models.py          # Database models
│   ├── routes/            # API endpoints
│   ├── agents/            # AI agents
│   └── requirements.txt    # Python packages
├── frontend/              # Web dashboard
│   ├── index.html
│   ├── *.html             # 9 pages
│   ├── css/style.css
│   └── js/                # 3 modules
└── docs/                  # Documentation
    ├── ARCHITECTURE.md
    ├── API_SPECIFICATION.md
    └── README.md
```

---

## ✅ Verification Checklist

After starting the app, verify it's working:

- [ ] Backend running at `http://localhost:5000`
- [ ] Frontend running at `http://localhost:8000`
- [ ] Landing page loads without errors
- [ ] Can click "Register" button
- [ ] Can create new account
- [ ] Dashboard loads after login
- [ ] Can navigate to all pages
- [ ] Preferences wizard works
- [ ] API calls are successful (check browser console)

---

## 🎓 Learning Resources

### Backend
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/)
- [RESTful API Design](https://restfulapi.net/)
- [NumPy Vectorization](https://numpy.org/doc/stable/)

### Frontend
- [MDN Web Docs](https://developer.mozilla.org/)
- [CSS Grid Layout](https://css-tricks.com/snippets/css/complete-guide-grid/)
- [JavaScript Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [LocalStorage API](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)

---

## 🤝 Support

If you encounter issues:

1. Check the browser console for errors (F12)
2. Check the backend console for errors
3. Review the relevant documentation
4. Check the troubleshooting section above
5. See the project README files

---

## 🎉 You're Ready!

The application is now running and ready to use. 

**Happy matching! 🏠👥**

---

**Last Updated:** February 25, 2024
