/*
FILE PATH: frontend/src/api.js
ACTION: REPLACE ENTIRE FILE
*/
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE });

// Attach the JWT (if we have one) to every outgoing request automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("cctv_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// If a protected call comes back 401 (expired/invalid token), force re-login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("cctv_token");
      localStorage.removeItem("cctv_username");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// --- Auth ---
export const login = (username, password) => {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  return api
    .post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    })
    .then((r) => r.data);
};

// --- Read-only data ---
export const getEvents = (eventType) =>
  api.get("/events", { params: eventType ? { event_type: eventType } : {} }).then((r) => r.data);
export const getAlerts = () => api.get("/alerts").then((r) => r.data);
export const getStatistics = () => api.get("/statistics").then((r) => r.data);
export const getKnownFaces = () => api.get("/known-faces").then((r) => r.data);
export const getCameras = () => api.get("/camera/list").then((r) => r.data);
export const getHealth = () => api.get("/health").then((r) => r.data);
export const getZone = (cameraId) => api.get(`/zones/${cameraId}`).then((r) => r.data);

// --- Unknown persons (Requirements 8-11) ---
export const getUnknownPersons = () => api.get("/unknown-persons").then((r) => r.data);
export const getUnknownPerson = (id) => api.get(`/unknown-persons/${id}`).then((r) => r.data);
export const getUnknownSightings = (id) =>
  api.get(`/unknown-persons/${id}/sightings`).then((r) => r.data);
export const convertUnknownToKnown = (id, name) =>
  api.post(`/unknown-persons/${id}/convert-to-known`, { name }).then((r) => r.data);

// --- Mutating (require login) ---
export const addCamera = (name, source) =>
  api.post("/camera/add", { name, source }).then((r) => r.data);

export const startCamera = (cameraId) =>
  api.post(`/camera/start?camera_id=${cameraId}`).then((r) => r.data);

export const stopCamera = (cameraId) =>
  api.post(`/camera/stop?camera_id=${cameraId}`).then((r) => r.data);

export const registerFace = (name, files) => {
  const form = new FormData();
  form.append("name", name);
  files.forEach((f) => form.append("files", f));
  return api.post("/register-face", form).then((r) => r.data);
};

export const deleteFace = (faceId) =>
  api.delete(`/known-faces/${faceId}`).then((r) => r.data);

export const saveZone = (cameraId, points) =>
  api.post("/zones", { camera_id: cameraId, points }).then((r) => r.data);

export const deleteZone = (cameraId) =>
  api.delete(`/zones/${cameraId}`).then((r) => r.data);

// --- Helpers ---
// Preserves the category subfolder (known/unknown/restricted/forensic) now
// used in snapshot_path, instead of just the filename. Old flat-folder
// paths (saved before this change) still resolve fine via the fallback.
export const snapshotUrl = (path) => {
  if (!path) return null;
  const marker = "snapshots/";
  const normalized = path.replace(/\\/g, "/");
  const idx = normalized.indexOf(marker);
  const relative = idx >= 0 ? normalized.slice(idx + marker.length) : normalized.split("/").pop();
  return `${API_BASE}/snapshots/${relative}`;
};

export const videoFeedUrl = (cameraId) => {
  const token = localStorage.getItem("cctv_token") || "";
  return `${API_BASE}/video_feed/${cameraId}?token=${encodeURIComponent(token)}`;
};

export { API_BASE };