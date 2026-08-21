import { useEffect, useState } from "react";

import { api } from "./api";
import { useAuthStore } from "./auth-store";
import type { CurrentUser } from "../types/auth";

export function useCurrentUser() {
  const { access, user, setUser } = useAuthStore();
  const [loading, setLoading] = useState(!user);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!access || user) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    api
      .get<CurrentUser>("/auth/me/")
      .then(({ data }) => {
        if (!cancelled) setUser(data);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load your profile.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [access, user, setUser]);

  return { user, loading, error };
}
