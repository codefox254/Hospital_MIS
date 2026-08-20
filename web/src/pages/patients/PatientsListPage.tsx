import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuthStore } from "../../lib/auth-store";
import { usePatients } from "./hooks";

export function PatientsListPage() {
  const [search, setSearch] = useState("");
  const { data, isLoading, isError } = usePatients(search);
  const canRegister = useAuthStore((s) => s.hasPermission("patients.patient.create"));

  return (
    <div>
      <div className="page-header">
        <h1>Patients</h1>
        {canRegister && (
          <Link to="/patients/new" className="button-primary">
            + Register patient
          </Link>
        )}
      </div>

      <input
        type="search"
        placeholder="Search by name, MRN, phone, or national ID"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="search-input"
      />

      {isLoading && <p>Loading…</p>}
      {isError && <p className="form-error">Could not load patients.</p>}

      {data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>MRN</th>
              <th>Name</th>
              <th>Gender</th>
              <th>Date of birth</th>
              <th>Phone</th>
            </tr>
          </thead>
          <tbody>
            {data.results.length === 0 && (
              <tr>
                <td colSpan={5}>No patients found.</td>
              </tr>
            )}
            {data.results.map((patient) => (
              <tr key={patient.id}>
                <td>{patient.mrn}</td>
                <td>
                  <Link to={`/patients/${patient.id}`}>
                    {patient.first_name} {patient.last_name}
                  </Link>
                  {patient.is_provisional && <span className="badge">Provisional</span>}
                </td>
                <td>{patient.gender}</td>
                <td>{patient.date_of_birth}</td>
                <td>{patient.phone}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
