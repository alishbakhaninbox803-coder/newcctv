import { useState } from "react";
import { registerFace, deleteFace, snapshotUrl } from "../api";

const MAX_FILE_SIZE_MB = 8;

export default function RegisterFace({ onRegistered, knownFaces = [] }) {
  const [name, setName] = useState("");
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState("");

  const handleFileChange = (e) => {
    const selected = Array.from(e.target.files);
    const invalid = selected.filter(
      (f) => f.type !== "image/jpeg" || f.size > MAX_FILE_SIZE_MB * 1024 * 1024
    );

    if (invalid.length > 0) {
      setFiles([]);
      e.target.value = ""; // reset input so the same file can be re-picked after fixing
      setStatus(
        "❌ Only JPG/JPEG photos are allowed (max 8MB each). Please compress your picture and upload it here."
      );
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
      const result = await registerFace(name, files);
      setStatus(`✅ Registered ${result.name} (${result.photo_count} photo(s) used)`);
      setName("");
      setFiles([]);
      onRegistered?.();
    } catch (err) {
      setStatus(`❌ ${err.response?.data?.detail || "Failed"}`);
    }
  };

  const handleDelete = async (id, personName) => {
    if (!confirm(`Remove ${personName} from known members?`)) return;
    await deleteFace(id);
    onRegistered?.();
  };

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-900 p-4">
      <h2 className="font-semibold mb-1">Register a Known Member</h2>
      <p className="text-xs text-gray-500 mb-3">
        Upload 2-4 clear, front-facing photos (different angles/lighting) for best recognition accuracy.
        JPG/JPEG only, max {MAX_FILE_SIZE_MB}MB each.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2 mb-4">
        <input
          className="bg-gray-800 rounded px-3 py-2 text-sm"
          placeholder="Full name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          type="file"
          accept=".jpg,.jpeg,image/jpeg"
          multiple
          className="text-sm"
          onChange={handleFileChange}
        />
        {files.length > 0 && (
          <p className="text-xs text-gray-400">{files.length} photo(s) selected</p>
        )}
        <button className="bg-blue-600 hover:bg-blue-500 rounded px-4 py-2 text-sm">
          Register Face
        </button>
        {status && <p className="text-xs text-gray-400">{status}</p>}
      </form>

      {knownFaces.length > 0 && (
        <div className="space-y-2 border-t border-gray-800 pt-3">
          <p className="text-xs text-gray-400 mb-1">Registered members</p>
          {knownFaces.map((f) => (
            <div
              key={f.id}
              className="flex items-center justify-between bg-gray-800 rounded px-3 py-2"
            >
              <div className="flex items-center gap-2">
                {f.photo_path && (
                  <img
                    src={snapshotUrl(f.photo_path)}
                    alt={f.name}
                    className="w-8 h-8 object-cover rounded-full"
                  />
                )}
                <span className="text-sm">{f.name}</span>
                <span className="text-xs text-gray-500">({f.photo_count} photos)</span>
              </div>
              <button
                onClick={() => handleDelete(f.id, f.name)}
                className="text-xs bg-red-600 hover:bg-red-500 rounded px-3 py-1"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}