# 📍 Family Location Sharing

A consent-based family location-sharing web application built with Flask and SQLite.

The application allows users to create or join families, manage family membership, and voluntarily share their current location with approved family members.

---

## 🚀 Features

### 👨‍👩‍👧 Family Management
- Create a family account
- Join an existing family
- Family-specific usernames and passwords
- Approve or reject membership requests
- Remove family members
- Switch between approved families

### 👤 User Management
- Personal user accounts
- Password hashing
- Member login/logout
- Family-specific permissions
- Admin and member roles

### 📍 Location Sharing
- Start location sharing voluntarily
- Stop location sharing at any time
- Browser-based location access
- Automatic location updates
- Last known location
- Family map using Leaflet

### 🔐 Privacy & Security
- Location is shared only when the user enables sharing
- Location is hidden when sharing is OFF
- Family membership authorization
- Family-specific location access
- Admin-only family management
- Members cannot access another family's data
- Removed members lose access to the family
- Passwords are stored using password hashing
- Secret key can be supplied through an environment variable

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application logic |
| Flask | Web framework |
| SQLite | Database |
| HTML | Frontend structure |
| CSS | User interface |
| JavaScript | Dynamic functionality |
| Leaflet.js | Interactive maps |
| OpenStreetMap | Map tiles |
| Werkzeug | Password hashing |
| Git & GitHub | Version control |

---

## 🏗️ Application Architecture

```text
User
 │
 ▼
Flask Web Application
 │
 ├── Authentication
 │
 ├── Family Management
 │
 ├── Membership Management
 │
 ├── Location Sharing
 │
 └── Family Map
 │
 ▼
SQLite Database
