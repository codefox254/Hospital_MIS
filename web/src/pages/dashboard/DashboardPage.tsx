import { useAuthStore } from "../../lib/auth-store";

/**
 * Solution Spec §7.2.1 describes KPI cards (Today's Patients, OPD Visits,
 * Inpatients, Bed Occupancy, Revenue Today) with trend deltas — none of
 * that data is exposed by any backend endpoint today (no dashboard/
 * analytics aggregation app exists yet, and Inpatients/Bed Occupancy
 * aren't built at all). Rendering fabricated numbers would be worse than
 * an honest placeholder, so this stays minimal until that API exists.
 */
export function DashboardPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div>
      <h1>Welcome{user ? `, ${user.first_name || user.email}` : ""}</h1>
      <p>
        {user?.facility.name} ({user?.facility.code})
      </p>
    </div>
  );
}
