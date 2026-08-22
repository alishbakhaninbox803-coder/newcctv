# AICCTV
# AI-Based Smart CCTV Surveillance System

An AI-powered CCTV system for **real-time object detection, face recognition, person tracking, zone-based trespass detection, live streaming, and Unknown-person management**.

## ✨ Features

* 🎥 Real-time CCTV live streaming
* 🤖 YOLOv8 object detection
* 👤 InsightFace face recognition
* 🏃 ByteTrack person tracking
* 🔍 Face quality & front-facing checks
* 🆔 Stable `Unknown-NNN` identification
* 📁 Separate Known/Unknown snapshot folders
* 🖼️ Multiple snapshots per Unknown person
* 👥 Unknown Persons management
* 🔄 Mark Unknown as Known
* 🚨 Zone-based trespass alerts
* 📊 Events, Alerts, Stats & Health dashboard
* 🔐 JWT-based admin authentication
* 💬 WhatsApp Cloud API alerts
* 🐘 PostgreSQL + pgvector
* ⚡ Redis Streams
* 🐳 Docker Compose

## 🛠️ Tech Stack

**Frontend:** React, Vite, Tailwind CSS
**Backend:** FastAPI, Python
**AI:** YOLOv8, InsightFace, ByteTrack
**Database:** PostgreSQL + pgvector
**Queue:** Redis Streams
**Notifications:** WhatsApp Cloud API
**Deployment:** Docker Compose

## 📂 Snapshot Storage

```text
data/
├── known/
├── unknown/
│   ├── Unknown-001/
│   │   ├── snapshot_001.jpg
│   │   ├── snapshot_002.jpg
│   │   └── ...
│   └── Unknown-002/
├── restricted/
└── forensic/
```

**One Unknown person = One ID = One folder = Multiple snapshots.**

## 🚀 Run

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Or run both:

```bash
python run_all.py
```

## 🔄 Recognition Flow

```text
Camera
  ↓
Face Detection
  ↓
Quality & Orientation Check
  ↓
Known Match?
 ├── YES → Known Person
 └── NO  → Check Unknown Database
             ├── Match → Existing Unknown ID
             └── No Match → New Unknown ID
```

Blurry, low-quality, or non-front-facing faces are ignored before creating snapshots or Unknown IDs.

## 📌 Project Goal

To provide an intelligent, real-time CCTV surveillance system capable of **recognizing known people, tracking unknown people, managing snapshots, detecting trespassing, and providing automated security alerts**.
