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
* `RESTRICTED_OBJECTS` — Comma-separated YOLO class names (`backpack,laptop,cell phone,handbag,suitcase`)
* `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ADMIN_NUMBER` — Optional WhatsApp Cloud API credentials

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

## 🖥️ Dashboard Pages

1. **Dashboard** (`/`) — Overview of live camera feeds, recent alerts, and real-time statistics.
2. **Live Feed** — Clean, low-latency MJPEG video streaming for all connected cameras.
3. **Events** (`/events`) — Filterable log of all security events, weapon sightings, and recognition logs.
4. **Alerts** (`/alerts`) — Critical trespass, weapon, and restricted-object alerts with snapshot preview.
5. **Unknown Persons** (`/unknown-persons`) — Visual gallery of detected unknown individuals with option to convert to Known.
6. **Persons Manager** (`/persons`) — Register known persons with multiple face photos and manage face embeddings.
7. **Zone Editor** (`/zone-editor`) — Interactive canvas to draw custom polygon intrusion detection zones over camera feeds.
8. **Health** (`/health`) — Live status of API, Database, Redis, and individual camera worker threads.

---

## 🧪 Running Unit Tests

Run the complete test suite (covering weapon engine, temporal tracker, polygon filters, and clean feed verification):

```bash
cd backend
python -m unittest discover -s tests -v
```

---

## 📄 License

This project is licensed under the MIT License.
