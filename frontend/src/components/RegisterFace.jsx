import { useState } from "react";
import {
  registerFace,
  deleteFace,
  snapshotUrl,
  getFacePhotos,
  addFacePhoto,
  deleteFacePhoto,
  setCoverPhoto,
} from "../api";

function PersonProfile({ face, onClose, onChanged }) {
  const [photos, setPhotos] = useState(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  const refreshPhotos = async () => {
    setPhotos(await getFacePhotos(face.id));
  };

  useState(() => {
    refreshPhotos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAddPhoto = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setStatus("Adding photo...");
    try {
      await addFacePhoto(face.id, file);
      setStatus("✅ Photo added");
      await refreshPhotos();
      onChanged?.();
    } catch (err) {
      setStatus(`❌ ${err.response?.data?.detail || "Failed to add photo"}`);
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  };

  const handleDeletePhoto = async (embeddingId) => {
    if (!confirm("Delete this photo?")) return;
    setBusy(true);
    try {
      await deleteFacePhoto(face.id, embeddingId);
      await refreshPhotos();
      onChanged?.();
    } catch (err) {
      setStatus(`❌ ${err.response?.data?.detail || "Failed to delete photo"}`);
    } finally {
      setBusy(false);
    }
  };

  const handleSetCover = async (embeddingId) => {
    setBusy(true);
    try {
      await setCoverPhoto(face.id, embeddingId);
      await refreshPhotos();
      onChanged?.();
    } catch (err) {
      setStatus(`❌ ${err.response?.data?.detail || "Failed to set cover photo"}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-2 bg-gray-950 border border-gray-700 rounded-lg p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium">{face.name}</p>
          <p className="text-xs text-gray-500">
            {[face.company, face.branch, face.role].filter(Boolean).join(" • ") || "No profile details"}
          </p>
        </div>
        <button onClick={onClose} className="text-xs text-gray-400 hover:text-white">
          Close
        </button>
      </div>

      <div>
        <label className="text-xs text-gray-400 mb-1 block">
          Photos ({photos?.length ?? "…"}/4)
        </label>
        <div className="grid grid-cols-4 gap-2">
          {photos?.map((p) => (
            <div key={p.id} className="relative group">
              <img
                src={snapshotUrl(p.photo_path)}
                alt="reference"
                className={`w-full aspect-square object-cover rounded ${
                  p.is_cover ? "ring-2 ring-blue-500" : ""
                }`}
              />
              {p.is_cover && (
                <span className="absolute top-1 left-1 text-[10px] bg-blue-600 rounded px-1">
                  Cover
                </span>
              )}
              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition flex flex-col items-center justify-center gap-1 rounded">
                {!p.is_cover && (
                  <button
                    onClick={() => handleSetCover(p.id)}
                    disabled={busy}
                    className="text-[10px] bg-blue-600 hover:bg-blue-500 rounded px-2 py-0.5"
                  >
                    Set as cover
                  </button>
                )}
                <button
                  onClick={() => handleDeletePhoto(p.id)}
                  disabled={busy}
                  className="text-[10px] bg-red-600 hover:bg-red-500 rounded px-2 py-0.5"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
          {photos && photos.length < 4 && (
            <label className="w-full aspect-square rounded border border-dashed border-gray-600 flex items-center justify-center text-xs text-gray-500 cursor-pointer hover:border-gray-400">
              + Add
              <input type="file" accept=".jpg,.jpeg,image/jpeg" className="hidden" onChange={handleAddPhoto} />
            </label>
          )}
        </div>
      </div>
      {status && <p className="text-xs text-gray-400">{status}</p>}
    </div>
  );
}

export default function RegisterFace({ onRegistered, knownFaces = [] }) {
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [branch, setBranch] = useState("");
  const [role, setRole] = useState("");
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState("");
  const [expandedId, setExpandedId] = useState(null);

  const handleFileChange = (e) => {
    const selected = Array.from(e.target.files);
    const nonJpg = selected.filter(
      (f) => !/\.(jpe?g)$/i.test(f.name) && f.type !== "image/jpeg"
    );
    if (nonJpg.length > 0) {
      setStatus(
        `❌ Only JPG/JPEG photos are supported. Rejected: ${nonJpg.map((f) => f.name).join(", ")}`
      );
      const jpgOnly = selected.filter((f) => !nonJpg.includes(f));
      setFiles(jpgOnly);
      return;
    }
    setStatus("");
    setFiles(selected);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || files.length === 0) return;
    setStatus("Registering...");
    try {
      const result = await registerFace(name, files, { company, branch, role });
      setStatus(`✅ Registered ${result.name} (${result.photo_count} photo(s) used)`);
      setName("");
      setCompany("");
      setBranch("");
      setRole("");
      setFiles([]);
      onRegistered?.();
    } catch (err) {
      setStatus(`❌ ${err.response?.data?.detail || "Failed"}`);
    }
  };

  const handleDelete = async (id, personName) => {
    if (!confirm(`Remove ${personName} from known members?`)) return;
    await deleteFace(id);
    if (expandedId === id) setExpandedId(null);
    onRegistered?.();
  };

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-900 p-4">
      <h2 className="font-semibold mb-1">Register a Known Member</h2>
      <p className="text-xs text-gray-500 mb-3">
        Only <span className="text-gray-300 font-medium">JPG/JPEG</span> photos are supported.
        Upload <span className="text-gray-300 font-medium">2–4 clear, front-facing photos</span>
        {" "}(different angles/lighting) for best recognition accuracy.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2 mb-4">
        <input
          className="bg-gray-800 rounded px-3 py-2 text-sm"
          placeholder="Full name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <div className="grid grid-cols-3 gap-2">
          <input
            className="bg-gray-800 rounded px-3 py-2 text-sm"
            placeholder="Company / Organization"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
          />
          <input
            className="bg-gray-800 rounded px-3 py-2 text-sm"
            placeholder="Branch / Location"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
          />
          <input
            className="bg-gray-800 rounded px-3 py-2 text-sm"
            placeholder="Role / Designation"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          />
        </div>
        <input
          type="file"
          accept=".jpg,.jpeg,image/jpeg"
          multiple
          className="text-sm"
          onChange={handleFileChange}
        />
        {files.length > 0 && (
          <p className="text-xs text-gray-400">{files.length} JPG photo(s) selected</p>
        )}
        <button className="bg-blue-600 hover:bg-blue-500 rounded px-4 py-2 text-sm">
          Register Face
        </button>
        {status && <p className="text-xs text-gray-400">{status}</p>}
      </form>

      {knownFaces.length > 0 && (
        <div className="space-y-2 border-t border-gray-800 pt-3">
          <p className="text-xs text-gray-400 mb-1">Registered members (click a name to view profile)</p>
          {knownFaces.map((f) => (
            <div key={f.id}>
              <div className="flex items-center justify-between bg-gray-800 rounded px-3 py-2">
                <div
                  className="flex items-center gap-2 cursor-pointer flex-1"
                  onClick={() => setExpandedId(expandedId === f.id ? null : f.id)}
                >
                  {f.photo_path && (
                    <img
                      src={snapshotUrl(f.photo_path)}
                      alt={f.name}
                      className="w-8 h-8 object-cover rounded-full"
                    />
                  )}
                  <div>
                    <span className="text-sm">{f.name}</span>
                    <span className="text-xs text-gray-500 ml-2">({f.photo_count} photos)</span>
                    {(f.company || f.branch || f.role) && (
                      <div className="text-xs text-gray-500">
                        {[f.company, f.branch, f.role].filter(Boolean).join(" • ")}
                      </div>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(f.id, f.name)}
                  className="text-xs bg-red-600 hover:bg-red-500 rounded px-3 py-1"
                >
                  Delete
                </button>
              </div>
              {expandedId === f.id && (
                <PersonProfile
                  face={f}
                  onClose={() => setExpandedId(null)}
                  onChanged={onRegistered}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}