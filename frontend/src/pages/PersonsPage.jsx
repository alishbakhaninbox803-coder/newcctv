import { useEffect, useState, useCallback } from "react";
import { getKnownFaces } from "../api";
import RegisterFace from "../components/RegisterFace";

export default function PersonsPage() {
  const [knownFaces, setKnownFaces] = useState([]);

  const refresh = useCallback(async () => {
    setKnownFaces(await getKnownFaces());
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="p-6 space-y-4 max-w-2xl">
      <header>
        <h1 className="text-xl font-bold">Registered Persons</h1>
        <p className="text-sm text-gray-400">Manage known members eligible for face recognition</p>
      </header>
      <RegisterFace onRegistered={refresh} knownFaces={knownFaces} />
    </div>
  );
}
