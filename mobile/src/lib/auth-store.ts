import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import type { CurrentUser, TokenPair } from "../types/auth";

interface AuthState {
  access: string | null;
  refresh: string | null;
  user: CurrentUser | null;
  setTokens: (tokens: TokenPair) => void;
  setUser: (user: CurrentUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      access: null,
      refresh: null,
      user: null,
      setTokens: (tokens) => set({ access: tokens.access, refresh: tokens.refresh }),
      setUser: (user) => set({ user }),
      logout: () => set({ access: null, refresh: null, user: null }),
    }),
    {
      name: "fdo-health-auth",
      storage: createJSONStorage(() => AsyncStorage),
    },
  ),
);
