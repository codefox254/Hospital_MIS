import { useQuery } from "@tanstack/react-query";

import { api } from "./api";
import { useAuthStore } from "./auth-store";
import type { CurrentUser } from "../types/auth";

/** TRD §5.1: route guards check permissions before rendering — this is
 * the one query every guarded route depends on, so it's centralized here
 * rather than re-fetched ad hoc per screen. */
export function useCurrentUser() {
  const access = useAuthStore((s) => s.access);
  const setUser = useAuthStore((s) => s.setUser);

  return useQuery({
    queryKey: ["me"],
    enabled: !!access,
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const { data } = await api.get<CurrentUser>("/auth/me/");
      setUser(data);
      return data;
    },
  });
}
