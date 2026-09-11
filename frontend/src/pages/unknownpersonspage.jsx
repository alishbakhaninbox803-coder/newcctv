/*
FILE PATH: frontend/src/pages/UnknownPersonsPage.jsx
ACTION: CREATE NEW FILE
*/
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "../hooks/useAuth";
import {
  getUnknownPersons,
  getUnknownSightings,
  convertUnknownToKnown,
  deleteUnknownPerson,
  snapshotUrl,
} from "../api";

function unknownLabel(id) {
  return `Unknown-${String(id).padStart(3, "0")}`;
}

function ConvertForm({ personId, onDone }) {
  const { isAdmin } = useAuth();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const result = await convertUnknownToKnown(personId, name.trim());
      setSuccess(`Registered as ${result.name}`);
      onDone?.();
    } catch (err) {
      setError(err.response?.data?.detail || "Conversion failed");
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!isAdmin) return;
    if (!window.confirm(`Delete Unknown-${String(personId).padStart(3, "0")} and all sightings?`)) return;
    setBusy(true);
    setError("");
    try {
      await deleteUnknownPerson(personId);
      onDone?.();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete");
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex items-center gap-2 mt-2">
      <input
        className="bg-gray-800 rounded px-2 py-1 text-xs flex-1"
        placeholder="Full name"
        value={name}
        disabled={busy}
        onChange={(e) => setName(e.target.value)}
      />
      <button
        disabled={busy || !name.trim()}
        className="bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded px-3 py-1 text-xs whitespace-nowrap"
      >
        Mark as Known
      </button>
      {isAdmin && (
        <button
          type="button"
          disabled={busy}
          onClick={handleDelete}
          className="bg-red-700 hover:bg-red-600 disabled:opacity-50 rounded px-3 py-1 text-xs whitespace-nowrap text-white"
          title="Delete unknown person (Admin only)"
        >
          Delete
        </button>
      )}
      {error && <span className="text-xs text-red-400">{error}</span>}
      {success && <span className="text-xs text-green-400">{success}</span>}
    </form>
  );
}

function SightingsGallery({ personId }) {
  const [sightings, setSightings] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getUnknownSightings(personId)
      .then(setSightings)
      .catch(() => setError("Failed to load sightings"));
  }, [personId]);

  if (error) return <p className="text-xs text-red-400 mt-2">{error}</p>;
  if (sightings === null) return <p className="text-xs text-gray-500 mt-2">Loading sightings...</p>;
  if (sightings.length === 0) return <p className="text-xs text-gray-500 mt-2">No sightings recorded.</p>;

  return (
    <div className="mt-2 flex gap-2 flex-wrap">
      {sightings.map((s) => (
        <div key={s.id} className="text-center">
          {s.snapshot_path ? (
            <img
              src={snapshotUrl(s.snapshot_path)}
              alt="sighting"
              className="w-16 h-16 object-cover rounded"
            />
          ) : (
            <div className="w-16 h-16 rounded bg-gray-800" />
          )}
          <p className="text-[10px] text-gray-500 mt-0.5">{s.camera_name}</p>
          <p className="text-[10px] text-gray-600">
            {new Date(s.timestamp).toLocaleTimeString()}
          </p>
        </div>
      ))}
    </div>
  );
}

export default function UnknownPersonsPage() {
  const [persons, setPersons] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setPersons(await getUnknownPersons());
    } catch (err) {
      setError("Failed to load unknown persons. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="p-6 space-y-4 max-w-3xl">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Unknown Persons</h1>
          <p className="text-sm text-gray-400">
            One entry per distinct unknown individual, de-duplicated across sightings and
            cameras. Convert someone to a known member once you recognize them.
          </p>
        </div>
        <button
          onClick={refresh}
          className="text-xs bg-gray-800 hover:bg-gray-700 rounded px-3 py-1.5 whitespace-nowrap"
        >
          Refresh
        </button>
      </header>

      {loading && <p className="text-sm text-gray-500">Loading...</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}
      {!loading && !error && persons.length === 0 && (
        <p className="text-sm text-gray-500">No unknown persons recorded yet.</p>
      )}

      <div className="space-y-3">
        {persons.map((p) => (
          <div key={p.id} className="rounded-xl border border-gray-700 bg-gray-900 p-4">
            <div className="flex items-center gap-4">
              {p.representative_snapshot_path ? (
                <img
                  src={snapshotUrl(p.representative_snapshot_path)}
                  alt={unknownLabel(p.id)}
                  className="w-16 h-16 object-cover rounded-lg"
                />
              ) : (
                <div className="w-16 h-16 rounded-lg bg-gray-800 flex items-center justify-center text-xs text-gray-500">
                  no photo
                </div>
              )}

              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold text-sm">{unknownLabel(p.id)}</span>
                  <span className="text-xs bg-red-600/80 rounded px-2 py-0.5">
                    {p.detection_count} detection{p.detection_count === 1 ? "" : "s"}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  First seen: {new Date(p.first_seen).toLocaleString()}
                </p>
                <p className="text-xs text-gray-400">
                  Last seen: {new Date(p.last_seen).toLocaleString()}
                </p>
              </div>

              <button
                onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}
                className="text-xs bg-gray-800 hover:bg-gray-700 rounded px-3 py-1.5 whitespace-nowrap"
              >
                {expandedId === p.id ? "Hide details" : "View Details"}
              </button>
            </div>

            <ConvertForm personId={p.id} onDone={refresh} />

            {expandedId === p.id && <SightingsGallery personId={p.id} />}
          </div>
        ))}
      </div>
    </div>
  );
}