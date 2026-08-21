import { NavLink, Outlet } from "react-router-dom";

import { useAuthStore } from "../../lib/auth-store";
import { useCurrentUser } from "../../lib/useCurrentUser";

/**
 * Sidebar entries match the Solution Spec's reference UI order (§7.1) —
 * but only for modules that actually exist on the backend today
 * (Patients, Appointments, OPD, Laboratory, Pharmacy, Billing). The
 * Solution Spec's fuller list (Inpatients, Radiology, Insurance,
 * Inventory, HR & Payroll, Reports, Settings) is Phase 1+ backend that
 * hasn't been built — listing a nav item for it here would be a dead
 * link, not a preview.
 */
const NAV_ITEMS = [
  { to: "/", label: "Dashboard", permission: null },
  { to: "/patients", label: "Patients", permission: "patients.patient.view" },
  { to: "/appointments", label: "Appointments", permission: "appointments.appointment.view" },
  { to: "/opd", label: "OPD", permission: "opd.visit.view" },
  { to: "/laboratory", label: "Laboratory", permission: "laboratory.lab_order.view" },
  { to: "/pharmacy", label: "Pharmacy", permission: "pharmacy.prescription.view" },
  { to: "/billing", label: "Billing", permission: "billing.invoice.view" },
  { to: "/admin", label: "Admin", permission: "accounts.user.create" },
] as const;

export function AppLayout() {
  const { data: user, isLoading } = useCurrentUser();
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const logout = useAuthStore((s) => s.logout);

  if (isLoading) {
    return <div className="app-loading">Loading…</div>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">FDO Hospital</div>
        <nav>
          {NAV_ITEMS.filter((item) => !item.permission || hasPermission(item.permission)).map(
            (item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              >
                {item.label}
              </NavLink>
            ),
          )}
        </nav>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <span>{user ? `${user.first_name} ${user.last_name}`.trim() || user.email : ""}</span>
          <span className="topbar-facility">{user?.facility.name}</span>
          <button type="button" onClick={logout}>
            Sign out
          </button>
        </header>
        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
