import { useEffect, useState, useCallback } from "react";
import { useAuth } from "../hooks/useAuth";
import {
  getUnknownPersons,
  getUnknownPersonSightings,
  convertUnknownToKnown,
  deleteUnknownPerson,
  snapshotUrl,
} from "../api";

export default function UnknownReviewPage() {
  const { isAdmin } = useAuth();
  const [unknownPersons, setUnknownPersons] = useState([]);
  const [selected, setSelected] = useState(null);
  const [sightings, setSightings] = useState([]);
  const [name, setName] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setUnknownPersons(await getUnknownPersons());
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  const selectPerson = async (person) => {
    setSelected(person);
    setName("");
    setStatus("");
    setSightings(await getUnknownPersonSightings(person.id));
  };

  const handleMakeKnown = async () => {
    if (!selected || !name.trim()) return;
    setLoading(true);
    setStatus("Confirming...");
    try {
      const result = await convertUnknownToKnown(selected.id, name.trim());
      setStatus(`✅ Registered as ${result.name}`);
      setSelected(null);
      setSightings([]);
      await refresh();
    } catch (err) {
      setStatus(`❌ ${err.response?.data?.detail || "Failed to convert"}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (personToDelete = selected) => {
    if (!isAdmin) return;
    if (!personToDelete) return;
    const label = `Unknown-${String(personToDelete.id).padStart(3, "0")}`;
    if (!window.confirm(`Delete ${label} and all associated sightings?`)) return;
    setLoading(true);
    setStatus("Deleting...");
    try {
      await deleteUnknownPerson(personToDelete.id);
      setStatus(`✅ Deleted ${label}`);
      if (selected?.id === personToDelete.id) {
        setSelected(null);
        setSightings([]);
      }
      await refresh();
    } catch (err) {
      setStatus(`❌ ${err.response?.data?.detail || "Failed to delete"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <header>
        <h1 className="text-xl font-bold">Unknown Review</h1>
        <p className="text-sm text-gray-400">
          Each card below is one distinct unidentified person — every repeat sighting of them
          (any camera, any time) is grouped into the same card, not a separate one.
        </p>
      </header>

      <div className="grid grid-cols-3 gap-4">
        {/* Left: distinct unknown identities */}
        <div className="col-span-1 space-y-2 max-h-[70vh] overflow-y-auto pr-1">
          {unknownPersons.map((p) => (
            <div
              key={p.id}
              onClick={() => selectPerson(p)}
              className={`flex gap-3 p-2 rounded-lg cursor-pointer border transition ${
                selected?.id === p.id
                  ? "border-blue-600 bg-gray-800"
                  : "border-gray-800 bg-gray-900 hover:border-gray-700"
              }`}
            >
              {p.representative_snapshot_path ? (
                <img
                  src={snapshotUrl(p.representative_snapshot_path)}
                  alt={`Unknown-${p.id}`}
                  className="w-14 h-14 object-cover rounded"
                />
              ) : (
                <div className="w-14 h-14 rounded bg-gray-800 flex items-center justify-center text-xs text-gray-500">
                  —
                </div>
              )}
              <div className="text-xs text-gray-400">
                <div className="text-red-500 font-semibold">
                  Unknown-{String(p.id).padStart(3, "0")}
                </div>
                <div>{p.detection_count} sighting(s)</div>
                <div>Last: {p.last_seen ? new Date(p.last_seen).toLocaleString() : "—"}</div>
              </div>
            </div>
          ))}
          {unknownPersons.length === 0 && (
            <p className="text-sm text-gray-500 p-2">No unidentified people currently on file.</p>
          )}
        </div>

        {/* Right: review panel */}
        <div className="col-span-2">
          {selected ? (
            <div className="rounded-xl border border-gray-700 bg-gray-900 p-4 space-y-4">
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 rounded text-xs bg-red-600">
                  Unknown-{String(selected.id).padStart(3, "0")}
                </span>
                <span className="text-xs text-gray-400">
                  First seen {selected.first_seen ? new Date(selected.first_seen).toLocaleString() : "—"}
                </span>
              </div>

              <img
                src={snapshotUrl(selected.representative_snapshot_path)}
                alt="representative snapshot"
                className="w-40 h-40 object-cover rounded-lg"
              />

              <div>
                <label className="text-xs text-gray-400 mb-1 block">
                  Sighting history ({sightings.length})
                </label>
                <div className="max-h-40 overflow-y-auto space-y-1">
                  {sightings.map((s) => (
                    <div key={s.id} className="flex gap-2 items-center bg-gray-800 rounded px-2 py-1 text-xs text-gray-400">
                      {s.snapshot_path && (
                        <img src={snapshotUrl(s.snapshot_path)} className="w-8 h-8 object-cover rounded" />
                      )}
                      <span>{s.camera_name}</span>
                      <span>•</span>
                      <span>{s.timestamp ? new Date(s.timestamp).toLocaleString() : "—"}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs text-gray-400 mb-1 block">Register as known person</label>
                <input
                  className="w-full bg-gray-800 rounded px-3 py-2 text-sm"
                  placeholder="Full name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleMakeKnown}
                  disabled={!name.trim() || loading}
                  className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded px-4 py-2 text-sm font-medium"
                >
                  ✓ Make Known
                </button>
                <button
                  onClick={() => setSelected(null)}
                  disabled={loading}
                  className="bg-gray-800 hover:bg-gray-700 rounded px-4 py-2 text-sm"
                >
                  Cancel
                </button>
                {isAdmin && (
                  <button
                    type="button"
                    onClick={() => handleDelete(selected)}
                    disabled={loading}
                    className="ml-auto bg-red-600/80 hover:bg-red-600 disabled:opacity-40 text-white rounded px-3.5 py-2 text-sm font-medium flex items-center gap-1.5 transition"
                    title="Delete this unknown person (Admin only)"
                  >
                    🗑️ Delete Unknown
                  </button>
                )}
              </div>
              {status && <p className="text-xs text-gray-400">{status}</p>}
            </div>
          ) : (
            <p className="text-sm text-gray-500">Select an unknown identity on the left to review it.</p>
          )}
        </div>
      </div>
    </div>
  );
}