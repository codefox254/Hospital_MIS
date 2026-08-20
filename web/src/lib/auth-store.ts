import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { CurrentUser, TokenPair } from "../types/auth";

interface AuthState {
  access: string | null;
  refresh: string | null;
  user: CurrentUser | null;
  setTokens: (tokens: TokenPair) => void;
  setUser: (user: CurrentUser) => void;
  logout: () => void;
  hasPermission: (code: string) => boolean;
}

/**
 * Persisted to localStorage (TRD §5.3 — the offline-tolerance requirement
 * is specifically about in-progress clinical drafts, not auth, but tokens
 * surviving a refresh is the same mechanism and there's no reason to make
 * the user re-login on every tab close).
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      access: null,
      refresh: null,
      user: null,
      setTokens: (tokens) => set({ access: tokens.access, refresh: tokens.refresh }),
      setUser: (user) => set({ user }),
      logout: () => set({ access: null, refresh: null, user: null }),
      hasPermission: (code) => get().user?.permissions.includes(code) ?? false,
    }),
    { name: "fdo-hospital-auth" },
  ),
);
