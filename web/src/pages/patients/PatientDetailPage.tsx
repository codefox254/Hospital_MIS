import { useParams } from "react-router-dom";

import { usePatient } from "./hooks";

export function PatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: patient, isLoading, isError } = usePatient(id);

  if (isLoading) return <p>Loading…</p>;
  if (isError || !patient) return <p className="form-error">Patient not found.</p>;

  return (
    <div>
      <h1>
        {patient.first_name} {patient.last_name}
      </h1>
      <p className="patient-mrn">
        {patient.mrn}
        {patient.is_provisional && <span className="badge">Provisional</span>}
      </p>

      <dl className="detail-grid">
        <dt>Date of birth</dt>
        <dd>{patient.date_of_birth}</dd>
        <dt>Gender</dt>
        <dd>{patient.gender}</dd>
        <dt>Phone</dt>
        <dd>{patient.phone || "—"}</dd>
        <dt>Email</dt>
        <dd>{patient.email || "—"}</dd>
        <dt>National ID</dt>
        <dd>{patient.national_id || "—"}</dd>
        <dt>Blood group</dt>
        <dd>{patient.blood_group || "—"}</dd>
      </dl>
    </div>
  );
}
