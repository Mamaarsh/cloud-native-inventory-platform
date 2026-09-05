import { useCallback, useEffect, useMemo, useState } from "react";
import { getCurrentUser, requestTokens } from "@/api/auth-api";
import { AUTH_LOGOUT_EVENT } from "@/api/client";
import { AuthContext, type AuthProviderProps } from "@/auth/AuthContext";
import { tokenStorage } from "@/auth/token-storage";
import type { Role, TokenRequest, User } from "@/types";

export function AuthProvider({ children }: AuthProviderProps) {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    tokenStorage.clear();
    setCurrentUser(null);
  }, []);

  useEffect(() => {
    const handleForcedLogout = () => logout();
    window.addEventListener(AUTH_LOGOUT_EVENT, handleForcedLogout);
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, handleForcedLogout);
  }, [logout]);

  useEffect(() => {
    let active = true;

    async function restoreSession(): Promise<void> {
      if (!tokenStorage.getAccess() || !tokenStorage.getRefresh()) {
        setIsLoading(false);
        return;
      }

      try {
        const user = await getCurrentUser();
        if (active) setCurrentUser(user);
      } catch {
        if (active) logout();
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void restoreSession();
    return () => {
      active = false;
    };
  }, [logout]);

  const login = useCallback(async (credentials: TokenRequest) => {
    const tokens = await requestTokens(credentials);
    tokenStorage.set(tokens.access, tokens.refresh);
    try {
      setCurrentUser(await getCurrentUser());
    } catch (error: unknown) {
      tokenStorage.clear();
      throw error;
    }
  }, []);

  const hasRole = useCallback(
    (required: Role | Role[]) => {
      const roles = Array.isArray(required) ? required : [required];
      return roles.some((role) => currentUser?.groups.includes(role) ?? false);
    },
    [currentUser],
  );

  const value = useMemo(
    () => ({
      currentUser,
      isAuthenticated: currentUser !== null,
      isLoading,
      login,
      logout,
      hasRole,
    }),
    [currentUser, hasRole, isLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
