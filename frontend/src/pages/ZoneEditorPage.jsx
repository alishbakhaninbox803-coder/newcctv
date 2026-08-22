import { useEffect, useRef, useState, useCallback } from "react";
import { getCameras, getZone, saveZone, deleteZone, videoFeedUrl } from "../api";

export default function ZoneEditorPage() {
  const [cameras, setCameras] = useState([]);
  const [cameraId, setCameraId] = useState(null);
  const [points, setPoints] = useState([]); // in displayed-image pixel coords
  const [status, setStatus] = useState("");
  const imgRef = useRef(null);

  useEffect(() => {
    getCameras().then((c) => {
      setCameras(c);
      if (c.length > 0) setCameraId(c[0].id);
    });
  }, []);

  useEffect(() => {
    if (!cameraId) return;
    setPoints([]);
    getZone(cameraId).then((zone) => {
      if (zone && imgRef.current) {
        // stored points are in natural frame coords; convert to displayed coords once image is loaded
        const img = imgRef.current;
        const applyScaled = () => {
          const scaleX = img.clientWidth / img.naturalWidth;
          const scaleY = img.clientHeight / img.naturalHeight;
          setPoints(zone.points.map(([x, y]) => [x * scaleX, y * scaleY]));
        };
        if (img.complete && img.naturalWidth) applyScaled();
        else img.onload = applyScaled;
      }
    });
  }, [cameraId]);

  const handleImageClick = (e) => {
    const rect = e.target.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setPoints((p) => [...p, [x, y]]);
  };

  const handleSave = async () => {
    if (points.length < 3) {
      setStatus("Add at least 3 points to form a zone.");
      return;
    }
    const img = imgRef.current;
    const scaleX = img.naturalWidth / img.clientWidth;
    const scaleY = img.naturalHeight / img.clientHeight;
    const naturalPoints = points.map(([x, y]) => [x * scaleX, y * scaleY]);
    await saveZone(cameraId, naturalPoints);
    setStatus("✅ Zone saved — running camera will pick it up immediately.");
  };

  const handleClear = async () => {
    setPoints([]);
    await deleteZone(cameraId);
    setStatus("Zone cleared — whole frame will be monitored again.");
  };

  const activeCamera = cameras.find((c) => c.id === cameraId);
  const polygonStr = points.map((p) => p.join(",")).join(" ");

  return (
    <div className="p-6 space-y-4">
      <header>
        <h1 className="text-xl font-bold">Zone Editor</h1>
        <p className="text-sm text-gray-400">
          Click on the live feed to draw a polygon. Only detections inside this zone will trigger alerts.
        </p>
      </header>

      <div className="flex items-center gap-3">
        <select
          className="bg-gray-800 rounded px-3 py-2 text-sm"
          value={cameraId || ""}
          onChange={(e) => setCameraId(Number(e.target.value))}
        >
          {cameras.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} {c.is_active ? "(live)" : "(offline)"}
            </option>
          ))}
        </select>
        <button onClick={handleSave} className="bg-blue-600 hover:bg-blue-500 rounded px-4 py-2 text-sm">
          Save Zone
        </button>
        <button onClick={handleClear} className="bg-gray-700 hover:bg-gray-600 rounded px-4 py-2 text-sm">
          Clear Zone
        </button>
        {status && <span className="text-xs text-gray-400">{status}</span>}
      </div>

      {!activeCamera && <p className="text-sm text-gray-500">No cameras yet — add one from the Dashboard first.</p>}

      {activeCamera && !activeCamera.is_active && (
        <p className="text-sm text-yellow-500">
          Start this camera from the Dashboard first so its live feed is available to draw on.
        </p>
      )}

      {activeCamera && activeCamera.is_active && (
        <div className="relative inline-block border border-gray-700 rounded overflow-hidden">
          <img
            ref={imgRef}
            src={videoFeedUrl(cameraId)}
            alt="live feed"
            onClick={handleImageClick}
            className="block cursor-crosshair max-w-3xl"
          />
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            {points.length > 1 && (
              <polygon points={polygonStr} fill="rgba(59,130,246,0.25)" stroke="#3b82f6" strokeWidth="2" />
            )}
            {points.map(([x, y], i) => (
              <circle key={i} cx={x} cy={y} r="4" fill="#3b82f6" />
            ))}
          </svg>
        </div>
      )}
    </div>
  );
}
