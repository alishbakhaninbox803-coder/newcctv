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

// --- Mutating (require login) ---
export const addCamera = (name, source) =>
  api.post("/camera/add", { name, source }).then((r) => r.data);

export const startCamera = (cameraId) =>
  api.post(`/camera/start?camera_id=${cameraId}`).then((r) => r.data);

export const stopCamera = (cameraId) =>
  api.post(`/camera/stop?camera_id=${cameraId}`).then((r) => r.data);

export const registerFace = (name, files, extra = {}) => {
  const form = new FormData();
  form.append("name", name);
  if (extra.company) form.append("company", extra.company);
  if (extra.branch) form.append("branch", extra.branch);
  if (extra.role) form.append("role", extra.role);
  files.forEach((f) => form.append("files", f));
  return api.post("/register-face", form).then((r) => r.data);
};

export const deleteFace = (faceId) =>
  api.delete(`/known-faces/${faceId}`).then((r) => r.data);

export const saveZone = (cameraId, points) =>
  api.post("/zones", { camera_id: cameraId, points }).then((r) => r.data);

export const deleteZone = (cameraId) =>
  api.delete(`/zones/${cameraId}`).then((r) => r.data);

// --- Known/Unknown identification workflow ---
export const confirmKnownPerson = (eventId, knownFaceId) =>
  api.post(`/events/${eventId}/confirm-known`, { known_face_id: knownFaceId }).then((r) => r.data);

// --- Unknown Persons dashboard (dedicated per-identity folders) ---
export const getUnknownPersons = () => api.get("/unknown-persons").then((r) => r.data);
export const getUnknownPersonSightings = (unknownPersonId) =>
  api.get(`/unknown-persons/${unknownPersonId}/sightings`).then((r) => r.data);
export const convertUnknownToKnown = (unknownPersonId, name) =>
  api.post(`/unknown-persons/${unknownPersonId}/convert-to-known`, { name }).then((r) => r.data);
export const deleteUnknownPerson = (unknownPersonId) =>
  api.delete(`/unknown-persons/${unknownPersonId}`).then((r) => r.data);


// --- Known person profile: view / add / delete / set-cover photos ---
export const getFacePhotos = (faceId) => api.get(`/known-faces/${faceId}/photos`).then((r) => r.data);
export const addFacePhoto = (faceId, file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post(`/known-faces/${faceId}/photos`, form).then((r) => r.data);
};
export const deleteFacePhoto = (faceId, embeddingId) =>
  api.delete(`/known-faces/${faceId}/photos/${embeddingId}`).then((r) => r.data);
export const setCoverPhoto = (faceId, embeddingId) =>
  api.put(`/known-faces/${faceId}/cover/${embeddingId}`).then((r) => r.data);

// --- Helpers ---
// snapshot_path from the backend can be either flat ("data/snapshots/foo.jpg")
// or nested inside a per-person folder ("data/snapshots/unknown/Unknown-017/foo.jpg").
// The static mount serves everything under data/snapshots/, so we must keep
// the FULL relative path after "data/snapshots/", not just the filename.
export const snapshotUrl = (path) => {
  if (!path) return null;
  const normalized = path.replace(/\\/g, "/");
  const marker = "data/snapshots/";
  const markerIndex = normalized.indexOf(marker);
  const relative =
    markerIndex >= 0 ? normalized.slice(markerIndex + marker.length) : normalized.split("/").pop();
  const encodedPath = relative
    .split("/")
    .filter(Boolean)
    .map(encodeURIComponent)
    .join("/");
  return `${API_BASE}/snapshots/${encodedPath}`;
};

export const videoFeedUrl = (cameraId) => {
  const token = localStorage.getItem("cctv_token") || "";
  return `${API_BASE}/video_feed/${cameraId}?token=${encodeURIComponent(token)}`;
};

export { API_BASE };
