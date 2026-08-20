import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { useAuthStore } from "../../lib/auth-store";

/**
 * TRD §4.4/§5.2: the queue panel subscribes to a WebSocket rather than
 * polling — polling is the fallback, not the primary mechanism, given
 * clinical urgency. On any `queue_update` event this just invalidates the
 * TanStack Query cache and lets the normal refetch pull the new list,
 * rather than trying to hand-merge the pushed payload into query state —
 * simpler, and correct even if a message is missed or arrives out of
 * order, since the next refetch always reflects the server's real state.
 */
export function useQueueSocket(facilityId: string | undefined, departmentId: string | undefined) {
  const queryClient = useQueryClient();
  const access = useAuthStore((s) => s.access);

  useEffect(() => {
    if (!facilityId || !departmentId || !access) return;

    const apiBase = import.meta.env.VITE_API_BASE_URL as string;
    const wsBase = apiBase.replace(/^http/, "ws").replace(/\/api\/v1\/?$/, "");
    const url = `${wsBase}/ws/appointments/queue/${facilityId}/${departmentId}/?token=${access}`;

    const socket = new WebSocket(url);
    socket.onmessage = () => {
      queryClient.invalidateQueries({ queryKey: ["queue", departmentId] });
    };

    return () => socket.close();
  }, [facilityId, departmentId, access, queryClient]);
}
