import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import apiClient from "@/api/client";
import type { JwtPayload, TokenResponse } from "@/types/api";

interface AuthUser {
  id: string;
  role: JwtPayload["role"];
}

interface AuthContextValue {
  token: string | null;
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const TOKEN_STORAGE_KEY = "token";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const decodeJwtPayload = (token: string): JwtPayload => {
  const payload = token.split(".")[1];
  if (!payload) {
    throw new Error("Invalid JWT format");
  }

  const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
  const json = atob(padded);

  return JSON.parse(json) as JwtPayload;
};

const getValidAuthFromToken = (token: string): { token: string; user: AuthUser } | null => {
  const payload = decodeJwtPayload(token);
  const nowSeconds = Math.floor(Date.now() / 1000);

  if (payload.exp <= nowSeconds || !payload.sub || !payload.role) {
    throw new Error("Expired or invalid JWT payload");
  }

  return {
    token,
    user: {
      id: payload.sub,
      role: payload.role,
    },
  };
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);

    if (!storedToken) {
      setLoading(false);
      return;
    }

    try {
      const restored = getValidAuthFromToken(storedToken);
      if (restored) {
        setToken(restored.token);
        setUser(restored.user);
      }
    } catch {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.set("username", username);
    formData.set("password", password);

    const response = await apiClient.post<TokenResponse>("/auth/login", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    const accessToken = response.data.access_token;
    const nextAuth = getValidAuthFromToken(accessToken);

    if (!nextAuth) {
      throw new Error("Unable to decode token");
    }

    localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    setToken(nextAuth.token);
    setUser(nextAuth.user);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      loading,
      login,
      logout,
    }),
    [token, user, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
