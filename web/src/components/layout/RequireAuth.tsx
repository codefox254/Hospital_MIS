import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuthStore } from "../../lib/auth-store";

export function RequireAuth({ children }: { children: ReactNode }) {
  const access = useAuthStore((s) => s.access);
  if (!access) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

/** TRD §5.1: "a route the user can't access redirects rather than
 * renders-then-blocks" — this is the client-side UX guard only; the
 * server (HasModulePermission, on every request) is the real
 * enforcement and this can never substitute for it. */
export function RequirePermission({
  code,
  children,
}: {
  code: string;
  children: ReactNode;
}) {
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const user = useAuthStore((s) => s.user);

  if (!user) {
    // Permissions haven't loaded yet (useCurrentUser still in flight) —
    // AppLayout already blocks rendering until then, so this only
    // matters for a route mounted before that resolves.
    return null;
  }
  if (!hasPermission(code)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
