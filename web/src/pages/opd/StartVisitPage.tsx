import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiErrorMessage } from "../../lib/api";
import { staffName, useDepartments, useStaffUsers } from "../../lib/useLookups";
import { usePatients } from "../patients/hooks";
import { useStartVisit } from "./hooks";

/**
 * Walk-in style start only (patient/doctor/department) — the backend
 * also accepts an `appointment` field to hand off a checked-in
 * appointment directly (verified in the live UAT walkthrough), but
 * there's no queue-side "start visit for this checked-in patient" UI
 * hook yet to drive it from. Scoped out for this pass rather than
 * half-wired; see CHANGELOG.
 */
export function StartVisitPage() {
  const navigate = useNavigate();
  const { data: departments } = useDepartments();
  const { data: staff } = useStaffUsers();

  const [patientSearch, setPatientSearch] = useState("");
  const [patientId, setPatientId] = useState("");
  const [doctor, setDoctor] = useState("");
  const [department, setDepartment] = useState("");

  const { data: patientResults } = usePatients(patientSearch);
  const startVisit = useStartVisit();

  async function handleStart() {
    if (!patientId || !doctor || !department) return;
    try {
      const visit = await startVisit.mutateAsync({ patient: patientId, doctor, department });
      navigate(`/opd/${visit.id}`, { replace: true });
    } catch {
      // startVisit.error surfaces below.
    }
  }

  return (
    <div>
      <h1>Start OPD visit</h1>
      <div className="form-grid booking-grid">
        <div>
          <label htmlFor="patient-search">Patient</label>
          <input
            id="patient-search"
            placeholder="Search by name, MRN, or phone"
            value={patientSearch}
            onChange={(e) => {
              setPatientSearch(e.target.value);
              setPatientId("");
            }}
          />
          {patientSearch && !patientId && (
            <ul className="typeahead-results">
              {patientResults?.results.slice(0, 6).map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setPatientId(p.id);
                      setPatientSearch(`${p.first_name} ${p.last_name} (${p.mrn})`);
                    }}
                  >
                    {p.first_name} {p.last_name} — {p.mrn}
                  </button>
                </li>
              ))}
              {patientResults?.results.length === 0 && <li>No matches.</li>}
            </ul>
          )}
        </div>

        <div>
          <label htmlFor="department">Department</label>
          <select id="department" value={department} onChange={(e) => setDepartment(e.target.value)}>
            <option value="">Select a department</option>
            {departments?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="doctor">Attending doctor</label>
          <select id="doctor" value={doctor} onChange={(e) => setDoctor(e.target.value)}>
            <option value="">Select a doctor</option>
            {staff?.map((s) => (
              <option key={s.id} value={s.id}>
                {staffName(s)}
              </option>
            ))}
          </select>
        </div>

        {startVisit.isError && <p className="form-error">{apiErrorMessage(startVisit.error)}</p>}

        <button type="button" onClick={handleStart} disabled={!patientId || !doctor || !department}>
          {startVisit.isPending ? "Starting…" : "Start visit"}
        </button>
      </div>
    </div>
  );
}
