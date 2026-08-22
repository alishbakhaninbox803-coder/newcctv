import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Login() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch {
      setError("Incorrect username or password");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <form
        onSubmit={handleSubmit}
        className="bg-gray-900 border border-gray-700 rounded-xl p-8 w-full max-w-sm space-y-4"
      >
        <div>
          <h1 className="text-xl font-bold">🎥 Smart CCTV</h1>
          <p className="text-sm text-gray-400">Sign in to access the dashboard</p>
        </div>

        <div>
          <label className="text-xs text-gray-400">Username</label>
          <input
            className="w-full bg-gray-800 rounded px-3 py-2 text-sm mt-1"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs text-gray-400">Password</label>
          <input
            type="password"
            className="w-full bg-gray-800 rounded px-3 py-2 text-sm mt-1"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button className="w-full bg-blue-600 hover:bg-blue-500 rounded px-4 py-2 text-sm font-medium">
          Sign in
        </button>

        <p className="text-xs text-gray-500">
          Default credentials: <code>admin</code> / whatever you set as{" "}
          <code>ADMIN_PASSWORD</code> in your backend <code>.env</code> (default{" "}
          <code>cctv2024</code>).
        </p>
      </form>
    </div>
  );
}
