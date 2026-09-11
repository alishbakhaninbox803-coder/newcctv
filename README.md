# AI-Based Smart CCTV Surveillance System

An enterprise-grade, real-time CCTV surveillance system combining **real-time weapon detection, object detection, face recognition, person tracking, zone-based intrusion detection, clean live video streaming, and Unknown-person management** — built entirely with open-source tools.

---

## ✨ Key Features

* 🔫 **Modular Weapon Detection Engine** — Dedicated real-time weapon & threat recognition (Firearms, Knives, Explosives) with zero live-stream lag.
* 🎥 **Clean Live Video Streaming** — High-speed MJPEG video streaming delivered unannotated with zero intrusive bounding boxes in the live view.
* 🛡️ **Temporal Confirmation Tracker** — Per-camera sliding window confirmation (suppresses single-frame false positives) and alert cooldown suppression.
* 🤖 **Multi-Tier Object Detection** — High-speed continuous monitoring with configurable restricted object alerts (backpacks, laptops, suitcases).
* 👤 **InsightFace Face Recognition** — Multi-photo face embeddings with ArcFace (`buffalo_l` model) for robust recognition across angles and lighting.
* 🏃 **ByteTrack Person Tracking** — Continuous person tracking and trajectory monitoring across video frames.
* 🔍 **Face Quality & Orientation Checks** — Automatic filtering of blurry, low-quality, or non-front-facing faces.
* 🆔 **Stable Unknown-NNN Identification** — Automatic clustering and tracking of unregistered individuals with persistent IDs.
* 📁 **Categorized Snapshot Management** — Organized snapshot capture (`known/`, `unknown/`, `restricted/`, `forensic/`, `weapon/`).
* 🚨 **Interactive Zone-Based Trespass Alerts** — Custom polygon intrusion zones per camera via the interactive Zone Editor.
* 📊 **Full Analytics & Health Dashboard** — Real-time event log, alert history, system statistics, and camera worker health monitoring.
* 🔐 **Role-Based Access Control (RBAC)** — Two-role system (Admin/User) with secure JWT authentication, admin user management, and separate workspaces.
* 💬 **WhatsApp Cloud API Alerts** — Real-time instant messaging notifications with snapshot alerts.
* 🐘 **PostgreSQL + pgvector** — High-performance vector database for instant face similarity search.
* ⚡ **Redis Streams** — Event streaming pipeline decoupling detection workers from API consumers.
* 🐳 **Docker Compose Ready** — One-command infrastructure deployment for PostgreSQL and Redis.

---

## 🛠️ Tech Stack & Architecture

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | React, Vite, Tailwind CSS, React Router | Modern, responsive dashboard UI |
| **Backend** | FastAPI, Python 3.10+, Uvicorn | Async REST API & MJPEG streaming |
| **Weapon Engine** | Ultralytics YOLOv8 / YOLO26x | Specialized threat detection (`Gun`, `Knife`, `Explosive`, `Firearm`) |
| **Object Engine** | Ultralytics YOLOv8 (nano & medium) | 2-tier fast pass + forensic confirmation |
| **Face Engine** | InsightFace (`buffalo_l`), OpenCV | 512-d embeddings + cosine similarity |
| **Tracking** | ByteTrack | Real-time multi-object tracking |
| **Database** | PostgreSQL 16 + pgvector | Persistent event storage & vector search |
| **Queue / Stream** | Redis Streams | Pub/Sub & event streaming |
| **Notifications** | WhatsApp Cloud API | Automated security alert dispatch |
| **Containers** | Docker, Docker Compose | Containerized Postgres & Redis services |

---

## 🔄 System Processing Pipeline

```text
[Camera Stream / RTSP / Webcam]
            │
   (cv2.VideoCapture - Capture Thread)
            ├──► Every frame ──► MJPEG Buffer ──► Browser Live Feed (CLEAN, NO OVERLAYS)
            │                                      (/video_feed/{id})
            │
            └──► Every Nth frame ──► Detection Worker Queue
                                            │
         ┌──────────────────────────────────┼──────────────────────────────────┐
         ▼                                  ▼                                  ▼
[1. Weapon Detection Engine]     [2. General Object Engine]         [3. InsightFace Engine]
         │                                  │                                  │
  Detects Threats:                 Detects Objects:                   Extracts Face Embedding:
  Firearm, Knife, Explosive        Backpack, Laptop, Suitcase         ArcFace 512-d Vector
         │                                  │                                  │
  Polygon Zone Filter              Polygon Zone Filter                pgvector Match (<0.45):
         │                                  │                         ├── Match ──► Known Person
  Temporal Tracker                          │                         └── No Match ──► Unknown-NNN
  (Sliding Window Confirmed)                │                                  │
         │                                  │                                  │
         └──────────────────────────────────┴──────────────────────────────────┘
                                            │
                                  Trigger Security Alert
                                  ├── Save Snapshot (data/snapshots/)
                                  ├── Insert PostgreSQL Event
                                  ├── Stream to Redis / Dashboard
                                  └── Dispatch WhatsApp Notification
```

---

## 📂 Snapshot Storage Structure

```text
data/snapshots/
├── known/
│   └── [Person_Name]/
│       ├── photo_1.jpg
│       └── photo_2.jpg
├── unknown/
│   ├── Unknown-001/
│   │   ├── snapshot_001.jpg
│   │   └── snapshot_002.jpg
│   └── Unknown-002/
│       └── snapshot_001.jpg
├── restricted/
│   └── [Event_ID].jpg
├── forensic/
│   └── [Confirmation_ID].jpg
└── weapon/
    └── [Weapon_Event_ID].jpg
```

---

## 🚀 Quick Start Guide

### Prerequisites

* **Python 3.10+** — [python.org](https://www.python.org/downloads/)
* **Node.js 18+** — [nodejs.org](https://nodejs.org)
* **Docker Desktop** — [docker.com](https://www.docker.com/products/docker-desktop)

---

### Step 1 — Configure Environment Variables

```bash
cp .env.example .env
```

Key environment settings in `.env`:
* `DATABASE_URL` — PostgreSQL connection string (`postgresql://cctv:cctv123@localhost:5432/cctv_db`)
* `ADMIN_USERNAME` / `ADMIN_PASSWORD` — Admin credentials (default: `admin` / `cctv2024`)
* `JWT_SECRET` — Secret string for signing authentication tokens
* `WEAPON_DETECTION_ENABLED` — Toggle weapon detection (`true` / `false`)
* `WEAPON_MODEL_PATH` — Path to weapon model weights (e.g., `models/weapon/threat-yolov8n.pt` or `models/weapon/weapon-yolo26x/best.pt`)
* `WEAPON_CONFIDENCE` — Confidence threshold for weapon detection (default: `0.30`)
* `WEAPON_CONFIRMATION_COUNT` — Detections required within sliding window (default: `1`)
* `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_TO_NUMBER` — Optional Twilio alert credentials (supports WhatsApp sandbox/number or SMS)
* `PUBLIC_BASE_URL` — Optional public hostname/tunnel URL (e.g. ngrok) to attach snapshot images to Twilio alerts

---

### Step 2 — Start Database & Redis

Launch PostgreSQL (with pgvector) and Redis via Docker:

```bash
docker compose up postgres redis -d
```

---

### Step 3 — Run Backend

```bash
cd backend
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **Note:** On first startup, models and InsightFace `buffalo_l` weights are verified and active cameras in the database are automatically booted.

---

### Step 4 — Run Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Dashboard is accessible at `http://localhost:5173`.

---

## 👥 Role-Based Access Control (RBAC)

AICCTV includes a production-ready role-based access control system with **two fixed roles**: Admin and User.

### Roles & Permissions

#### **Admin Role**
Full system access including user management:
- ✅ Access complete dashboard with all features
- ✅ Manage cameras, zones, and detection settings
- ✅ View all events, alerts, and historical data
- ✅ Create, edit, and delete user accounts
- ✅ Reset user passwords
- ✅ Activate/deactivate users
- ✅ Access security settings

#### **User Role**
Limited access focused on people operations:
- ✅ Add known persons with face photos
- ✅ Promote unknown persons to known
- ✅ View personal dashboard
- ❌ Cannot create or manage other users
- ❌ Cannot access admin settings
- ❌ Cannot manage cameras or zones
- ❌ Cannot view system configuration

### Default Admin Credentials

```
Username: admin
Password: cctv2024  (from .env)
```

### Admin User Management

#### Create a New User (Admin Only)

Use the Admin Users page (`/users`) to create new users:

1. Click **"Create User"** button
2. Enter username, email, and password
3. Click **"Create"** — user is created with role="user"
4. User receives their credentials to log in

Alternatively, use the API:

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {admin_token}" \
  -d '{
    "username": "john_doe",
    "email": "john@company.com",
    "password": "secure_password"
  }'
```

#### List All Users (Admin Only)

```bash
curl -X GET http://localhost:8000/users \
  -H "Authorization: Bearer {admin_token}"
```

#### Reset User Password (Admin Only)

```bash
curl -X PUT http://localhost:8000/users/{user_id}/password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {admin_token}" \
  -d '{"password": "new_password"}'
```

#### Activate/Deactivate User (Admin Only)

```bash
curl -X PUT http://localhost:8000/users/{user_id} \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {admin_token}" \
  -d '{"is_active": false}'  # true to activate, false to deactivate
```

### Authentication Flow

1. **Login** (`POST /auth/login`)
   - Returns JWT token + user data with role information
   - Token valid for entire session

2. **Verify Auth** (`GET /auth/me`)
   - Frontend calls this on app startup
   - Returns current user data and role
   - Allows frontend to verify token and load role-specific UI

3. **Protected Endpoints**
   - All API endpoints require valid JWT token
   - Admin endpoints return 403 Forbidden if user is not admin
   - Frontend routes automatically redirect unauthorized users

### Frontend Workspaces

**Admin Workspace** (if role="admin")
- Dashboard
- Cameras
- Detections
- Known People
- Unknown People
- Zones
- Events
- Alerts
- System Health
- **Users** (admin-only)
- **Security Settings** (admin-only)

**User Workspace** (if role="user")
- Home
- Add Known Person
- Promote Unknown → Known

---



## 🖥️ Dashboard Pages

### Admin-Accessible Pages
1. **Dashboard** (`/`) — Overview of live camera feeds, recent alerts, and real-time statistics.
2. **Live Feed** — Clean, low-latency MJPEG video streaming for all connected cameras.
3. **Events** (`/events`) — Filterable log of all security events, weapon sightings, and recognition logs.
4. **Alerts** (`/alerts`) — Critical trespass, weapon, and restricted-object alerts with snapshot preview.
5. **Unknown Persons** (`/unknown-persons`) — Visual gallery of detected unknown individuals with option to convert to Known.
6. **Persons Manager** (`/persons`) — Register known persons with multiple face photos and manage face embeddings.
7. **Zone Editor** (`/zone-editor`) — Interactive canvas to draw custom polygon intrusion detection zones over camera feeds.
8. **Health** (`/health`) — Live status of API, Database, Redis, and individual camera worker threads.
9. **Users** (`/users`) — **[ADMIN ONLY]** Create, list, edit, and manage user accounts. Reset passwords, activate/deactivate users.
10. **Security Settings** (`/settings`) — **[ADMIN ONLY]** View security configuration and RBAC information.

### User-Accessible Pages
1. **User Home** (`/user/home`) — Welcome page with quick links to people operations.
2. **Add Known Person** (`/user/people/add`) — Register a new known person with face embeddings.
3. **Promote Unknown to Known** (`/user/people/promote`) — Convert unknown person detections to known person.

---

## 🔌 API Endpoints

### Authentication
- `POST /auth/login` — Login with username/password, returns JWT token + user data
- `GET /auth/me` — Get current authenticated user (used by frontend for auth verification)
- `POST /auth/seed-admin` — Create default admin user (run once on first startup)

### User Management (Admin-Only)
- `POST /users` — Create new user
- `GET /users` — List all users
- `GET /users/{id}` — Get user details
- `PUT /users/{id}` — Update user (email, is_active status)
- `PUT /users/{id}/password` — Reset user password

### All Endpoints
All endpoints require valid JWT token in `Authorization: Bearer {token}` header. Admin endpoints return `403 Forbidden` if user is not admin.

See [API Documentation](./docs/API.md) for complete endpoint reference.

---

## 🧪 Running Unit Tests

Run the complete test suite (covering weapon engine, temporal tracker, polygon filters, and clean feed verification):

```bash
cd backend
python -m unittest discover -s tests -v
```

---

## ❓ FAQ & Troubleshooting

### RBAC & Authentication

**Q: How do I reset the admin password?**
- Edit `.env` file and change `ADMIN_PASSWORD`
- Restart backend
- Old admin user will have updated credentials on next seed

**Q: Can I change a user's role from "user" to "admin"?**
- No. Roles are fixed at user creation. Only admins and users exist.
- To create an admin-equivalent user, manually update the database (not recommended)

**Q: What happens if a user is disabled (is_active=false)?**
- Disabled users cannot login and cannot access any endpoint
- Returns `403 Forbidden` if disabled user tries to use existing token

**Q: How do I delete a user?**
- Currently not available via API (intentional for data safety)
- Use `is_active=false` to disable instead
- Manual deletion available via database

**Q: Can users change their own password?**
- Not yet. Password reset requires admin action
- Admin can reset user password via `/users/{id}/password` endpoint

### General Troubleshooting

**Q: Backend won't start — "table users already exists"**
- Database already initialized. This is normal.
- If schema issues, drop tables and restart: `docker compose down && docker compose up postgres -d`

**Q: Frontend shows "Loading..." indefinitely**
- Check if backend is running: `curl http://localhost:8000/auth/me`
- Check browser console for errors
- Verify token in localStorage is valid

**Q: User can't login**
- Verify `is_active=true` in database
- Check password hash was stored correctly
- Verify username/email are unique in database

**Q: 403 Forbidden on admin endpoints**
- Verify user has `role="admin"` in database
- Check token is valid: `GET /auth/me` should return user with role="admin"

---

## 📚 Additional Resources

- [RBAC Implementation Report](./docs/RBAC_IMPLEMENTATION_REPORT.md) — Complete technical documentation
- [Quick Reference Guide](./docs/QUICK_REFERENCE.md) — API examples and role matrix
- [Deployment Guide](./docs/DEPLOYMENT.md) — Production deployment checklist

---

## 📄 License

This project is licensed under the MIT License.
