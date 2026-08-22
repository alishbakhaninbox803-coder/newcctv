import { useEffect, useState, useCallback } from "react";
import { getAlerts } from "../api";
import EventsTable from "../components/EventsTable";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);

  const refresh = useCallback(async () => {
    setAlerts(await getAlerts());
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  return (
    <div className="p-6 space-y-4">
      <header>
        <h1 className="text-xl font-bold">Alerts</h1>
        <p className="text-sm text-gray-400">
          Unknown persons, restricted objects, and forensic confirmations only
        </p>
      </header>
      <EventsTable events={alerts} />
    </div>
  );
}
