import { useState } from "react";

import { useAuthStore } from "../../lib/auth-store";
import { apiErrorMessage } from "../../lib/api";
import { useCreateFacility, useCreateUser, useDeactivateFacility, usePlatformStats } from "./hooks";

const FACILITY_TYPES = ["hospital", "clinic", "branch"] as const;

function SuperAdminDashboard() {
  const { data: stats, isLoading } = usePlatformStats();
  const createFacility = useCreateFacility();
  const createUser = useCreateUser();
  const deactivateFacility = useDeactivateFacility();

  const [facilityForm, setFacilityForm] = useState({
    name: "",
    code: "",
    type: "hospital" as (typeof FACILITY_TYPES)[number],
    address: "",
    phone: "",
  });
  const [adminForm, setAdminForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    facility: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const totals = (stats ?? []).reduce(
    (acc, f) => ({
      facilities: acc.facilities + 1,
      patients: acc.patients + f.patient_count,
      users: acc.users + f.active_user_count,
      appointmentsToday: acc.appointmentsToday + f.appointments_today,
    }),
    { facilities: 0, patients: 0, users: 0, appointmentsToday: 0 },
  );

  async function handleCreateFacility(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createFacility.mutateAsync(facilityForm);
      setNotice(`${facilityForm.name} onboarded.`);
      setFacilityForm({ name: "", code: "", type: "hospital", address: "", phone: "" });
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  async function handleCreateAdmin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createUser.mutateAsync({ ...adminForm, role: "Administrator" });
      setNotice(`Facility admin ${adminForm.email} created.`);
      setAdminForm({ email: "", password: "", first_name: "", last_name: "", facility: "" });
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Platform Dashboard</h1>
      </div>
      <p className="card-subtitle">Super Admin — cross-facility view, no patient-level data.</p>

      {error ? <p className="form-error">{error}</p> : null}
      {notice ? <p style={{ color: "var(--success-fg)" }}>{notice}</p> : null}

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">Facilities</div>
          <div className="stat-value">{totals.facilities}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total patients</div>
          <div className="stat-value">{totals.patients}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active staff</div>
          <div className="stat-value">{totals.users}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Appointments today</div>
          <div className="stat-value">{totals.appointmentsToday}</div>
        </div>
      </div>

      <h2 className="section-title">Facilities</h2>
      {isLoading ? (
        <p>Loading…</p>
      ) : (
        <div className="card-list">
          {(stats ?? []).map((f) => (
            <div key={f.id} className="modern-card">
              <div className="icon-badge lg">🏥</div>
              <div className="card-body">
                <div className="card-row">
                  <p className="card-title">
                    {f.name} <span className="card-subtitle">({f.code})</span>
                  </p>
                  <span className={f.is_active ? "pill pill-success" : "pill pill-neutral"}>
                    {f.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <p className="card-meta">
                  {f.patient_count} patients · {f.active_user_count} staff ·{" "}
                  {f.appointments_today} appointments today
                </p>
              </div>
              {f.is_active ? (
                <button
                  type="button"
                  className="inline-link"
                  onClick={() => deactivateFacility.mutate(f.id)}
                >
                  Deactivate
                </button>
              ) : null}
            </div>
          ))}
        </div>
      )}

      <h2 className="section-title">Onboard a new hospital</h2>
      <form className="form-panel" onSubmit={handleCreateFacility}>
        <h3>Create facility</h3>
        <label htmlFor="fac-name">Name</label>
        <input
          id="fac-name"
          required
          value={facilityForm.name}
          onChange={(e) => setFacilityForm({ ...facilityForm, name: e.target.value })}
        />
        <label htmlFor="fac-code">Code</label>
        <input
          id="fac-code"
          required
          value={facilityForm.code}
          onChange={(e) => setFacilityForm({ ...facilityForm, code: e.target.value })}
        />
        <label htmlFor="fac-type">Type</label>
        <select
          id="fac-type"
          value={facilityForm.type}
          onChange={(e) =>
            setFacilityForm({
              ...facilityForm,
              type: e.target.value as (typeof FACILITY_TYPES)[number],
            })
          }
        >
          {FACILITY_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <label htmlFor="fac-phone">Phone</label>
        <input
          id="fac-phone"
          value={facilityForm.phone}
          onChange={(e) => setFacilityForm({ ...facilityForm, phone: e.target.value })}
        />
        <button type="submit" className="button-primary" disabled={createFacility.isPending}>
          {createFacility.isPending ? "Creating…" : "Create facility"}
        </button>
      </form>

      <h2 className="section-title">Create a facility admin</h2>
      <form className="form-panel" onSubmit={handleCreateAdmin}>
        <h3>New facility admin account</h3>
        <label htmlFor="admin-facility">Facility</label>
        <select
          id="admin-facility"
          required
          value={adminForm.facility}
          onChange={(e) => setAdminForm({ ...adminForm, facility: e.target.value })}
        >
          <option value="">Select a facility…</option>
          {(stats ?? []).map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </select>
        <label htmlFor="admin-email">Email</label>
        <input
          id="admin-email"
          type="email"
          required
          value={adminForm.email}
          onChange={(e) => setAdminForm({ ...adminForm, email: e.target.value })}
        />
        <label htmlFor="admin-password">Temporary password</label>
        <input
          id="admin-password"
          type="password"
          required
          minLength={12}
          value={adminForm.password}
          onChange={(e) => setAdminForm({ ...adminForm, password: e.target.value })}
        />
        <label htmlFor="admin-first">First name</label>
        <input
          id="admin-first"
          value={adminForm.first_name}
          onChange={(e) => setAdminForm({ ...adminForm, first_name: e.target.value })}
        />
        <label htmlFor="admin-last">Last name</label>
        <input
          id="admin-last"
          value={adminForm.last_name}
          onChange={(e) => setAdminForm({ ...adminForm, last_name: e.target.value })}
        />
        <button type="submit" className="button-primary" disabled={createUser.isPending}>
          {createUser.isPending ? "Creating…" : "Create facility admin"}
        </button>
      </form>
    </div>
  );
}

function FacilityAdminDashboard() {
  const user = useAuthStore((s) => s.user);
  const createUser = useCreateUser();
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function handleCreateStaff(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createUser.mutateAsync(form);
      setNotice(`${form.email} added to ${user?.facility.name}.`);
      setForm({ email: "", password: "", first_name: "", last_name: "" });
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Facility Admin</h1>
      </div>
      <p className="card-subtitle">
        {user?.facility.name} ({user?.facility.code})
      </p>

      {error ? <p className="form-error">{error}</p> : null}
      {notice ? <p style={{ color: "var(--success-fg)" }}>{notice}</p> : null}

      <h2 className="section-title">Add a staff member</h2>
      <form className="form-panel" onSubmit={handleCreateStaff}>
        <h3>New account (this facility only)</h3>
        <label htmlFor="staff-email">Email</label>
        <input
          id="staff-email"
          type="email"
          required
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <label htmlFor="staff-password">Temporary password</label>
        <input
          id="staff-password"
          type="password"
          required
          minLength={12}
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
        <label htmlFor="staff-first">First name</label>
        <input
          id="staff-first"
          value={form.first_name}
          onChange={(e) => setForm({ ...form, first_name: e.target.value })}
        />
        <label htmlFor="staff-last">Last name</label>
        <input
          id="staff-last"
          value={form.last_name}
          onChange={(e) => setForm({ ...form, last_name: e.target.value })}
        />
        <button type="submit" className="button-primary" disabled={createUser.isPending}>
          {createUser.isPending ? "Creating…" : "Create staff account"}
        </button>
      </form>
    </div>
  );
}

export function AdminDashboardPage() {
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const isSuperAdmin = hasPermission("core.facility.view");

  return isSuperAdmin ? <SuperAdminDashboard /> : <FacilityAdminDashboard />;
}
