import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { login as apiLogin, api } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // On mount, check if user is already logged in
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("cctv_token");
      if (token) {
        try {
          // Try to fetch current user from backend
          const response = await api.get("/auth/me");
          setUser(response.data);
          setIsAuthenticated(true);
        } catch (err) {
          // Token is invalid or expired
          localStorage.removeItem("cctv_token");
          setIsAuthenticated(false);
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = useCallback(async (username, pass) => {
    const data = await apiLogin(username, pass);
    localStorage.setItem("cctv_token", data.access_token);
    setUser(data.user);
    setIsAuthenticated(true);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("cctv_token");
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  const username = user?.username || null;
  const role = user?.role || null;
  const isAdmin = role === "admin";

  return (
    <AuthContext.Provider value={{ user, username, role, isAdmin, isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
