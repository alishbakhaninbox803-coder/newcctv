import { createContext, useContext, useState, useCallback } from "react";
import { login as apiLogin } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [username, setUsername] = useState(localStorage.getItem("cctv_username"));

  const login = useCallback(async (user, pass) => {
    const data = await apiLogin(user, pass);
    localStorage.setItem("cctv_token", data.access_token);
    localStorage.setItem("cctv_username", data.username);
    setUsername(data.username);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("cctv_token");
    localStorage.removeItem("cctv_username");
    setUsername(null);
  }, []);

  const isAuthenticated = !!localStorage.getItem("cctv_token");

  return (
    <AuthContext.Provider value={{ username, login, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
