import { createContext } from "react";
import type { ReactNode } from "react";
import type { Role, TokenRequest, User } from "@/types";

export interface AuthContextValue {
  currentUser: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: TokenRequest) => Promise<void>;
  logout: () => void;
  hasRole: (role: Role | Role[]) => boolean;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export interface AuthProviderProps {
  children: ReactNode;
}
