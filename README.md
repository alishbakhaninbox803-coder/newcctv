# AI-Based Smart CCTV Surveillance System

An enterprise-grade, real-time CCTV surveillance system combining **real-time object detection, face recognition, person tracking, zone-based trespass detection, live video streaming, and Unknown-person management** — built entirely with open-source tools.

---

## ✨ Key Features

* 🎥 **Real-time Live Video Streaming** — Low-latency MJPEG video streaming directly in the browser dashboard.
* 🤖 **Two-Tier YOLOv8 Detection** — High-speed continuous monitoring (YOLOv8n) with automatic forensic confirmation pass (YOLOv8m) on detected anomalies.
* 👤 **InsightFace Face Recognition** — Multi-photo face embeddings with ArcFace (buffalo_l model) for robust recognition across angles and lighting.
* 🏃 **ByteTrack Person Tracking** — Continuous person tracking and trajectory monitoring across video frames.
* 🔍 **Face Quality & Orientation Checks** — Automatic filtering of blurry, low-quality, or non-front-facing faces.
* 🆔 **Stable Unknown-NNN Identification** — Automatic clustering and tracking of unregistered individuals with persistent IDs.
* 📁 **Snapshot Management** — Organized snapshot capture (Known, Unknown, Restricted Objects, and Forensic confirmations).
* 🚨 **Interactive Zone-Based Trespass Alerts** — Custom polygon intrusion zones per camera via the interactive Zone Editor.
* 📊 **Full Analytics & Health Dashboard** — Real-time event log, alert history, system statistics, and camera worker health monitoring.
* 🔐 **Role-Gated JWT Authentication** — Secure login and session management for administrative control.
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
| **Detection Engine** | Ultralytics YOLOv8 (nano & medium) | 2-tier fast pass + forensic confirmation |
| **Face Engine** | InsightFace (`buffalo_l`), OpenCV | 512-d embeddings + cosine similarity |
| **Tracking** | ByteTrack | Real-time multi-object tracking |
| **Database** | PostgreSQL 16 + pgvector | Persistent event storage & vector search |
| **Queue / Stream** | Redis Streams | Pub/Sub & event streaming |
| **Notifications** | WhatsApp Cloud API | Automated security alert dispatch |
| **Containers** | Docker, Docker Compose | Containerized Postgres & Redis services |

---

## 🔄 Recognition Flow

```text
               Camera Frame
                    │
                    ▼
           YOLOv8 Person Detection
                    │
                    ▼
        Face Quality & Orientation Check
         ├── Low Quality / Blurry ──► Ignored
         └── Valid Face
                    │
                    ▼
          InsightFace 512-d Embedding
                    │
                    ▼
         Vector Search (pgvector)
          ├── Match (Cosine < 0.45) ──► Known Person Event
          └── No Match
                    │
                    ▼
         Unknown Persons Cluster
          ├── Existing Cluster ──► Update Unknown-NNN (Add Snapshot)
          └── New Face ──────────► Register New Unknown-NNN Folder
```

---

## 📂 Snapshot Storage Structure

```text
data/
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
└── forensic/
    └── [Confirmation_ID].jpg
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

Edit `.env` and configure your settings:
* `DATABASE_URL` — PostgreSQL connection string (`postgresql://cctv:cctv123@localhost:5432/cctv_db`)
* `ADMIN_USERNAME` / `ADMIN_PASSWORD` — Admin login credentials (default: `admin` / `cctv2024`)
* `JWT_SECRET` — Secret string for signing authentication tokens
* `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ADMIN_NUMBER` — Optional WhatsApp Cloud API credentials
* `RESTRICTED_OBJECTS` — Comma-separated YOLO class names (e.g. `backpack,laptop,cell phone,handbag,suitcase,knife,gun`)

---

### Step 2 — Start Infrastructure Services

Launch PostgreSQL (with pgvector) and Redis using Docker Compose:

```bash
docker compose up postgres redis -d
```

---

### Step 3 — Run Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **Note:** The first run will automatically download the YOLOv8 models and InsightFace `buffalo_l` weights (~280MB).

---

### Step 4 — Run Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

### ⚡ Single-Command Startup

You can launch both the backend and frontend concurrently with:

```bash
python run_all.py
```

---

## 🖥️ Dashboard Pages

1. **Dashboard** (`/`) — Overview of live camera feeds, recent alerts, and real-time statistics.
2. **Live Feed** — Low-latency MJPEG video streaming for all connected cameras.
3. **Events** (`/events`) — Filterable log of all security events, object detections, and recognition logs.
4. **Alerts** (`/alerts`) — Critical trespass and restricted-object alerts with snapshot preview.
5. **Unknown Persons** (`/unknown-persons`) — Visual gallery of detected unknown individuals with option to convert to Known.
6. **Persons Manager** (`/persons`) — Register known persons with multiple face photos and manage face embeddings.
7. **Zone Editor** (`/zone-editor`) — Interactive canvas to draw custom polygon intrusion detection zones over camera feeds.
8. **Health** (`/health`) — Live status of API, Database, Redis, and individual camera worker threads.

---

## 🔒 Security & Privacy

* `.env` files, database passwords, and API keys are strictly excluded from version control.
* Mutating endpoints (registering faces, managing zones, starting camera workers) require JWT authentication.
* Model weights and local snapshot media directories are managed locally and ignored from Git.

---

## 📄 License

This project is licensed under the MIT License.
