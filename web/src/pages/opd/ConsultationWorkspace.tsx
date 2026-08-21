import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { apiErrorMessage } from "../../lib/api";
import { useAuthStore } from "../../lib/auth-store";
import { usePatientName } from "../../lib/useLookups";
import { formatStatusLabel, pillClass } from "../../lib/statusPill";
import {
  useAddAddendum,
  useAddDiagnosis,
  useAddenda,
  useCompleteConsultation,
  useConsultationForVisit,
  useDiagnoses,
  useRecordVitals,
  useUpdateConsultationDraft,
  useVisit,
  useVitalsForVisit,
} from "./hooks";
import type { DiagnosisType } from "../../types/opd";

/**
 * Solution Spec §7.2.3 describes a split-panel workspace with a
 * left-hand section list (Vitals / Chief Complaint / History /
 * Examination / Diagnosis / Investigations / Prescription / Procedures
 * / Notes / Documents). This builds the clinically load-bearing subset
 * — vitals, the draft note, diagnosis, lock, addendum — as one scrolling
 * workspace rather than the full split-panel chrome; Investigations/
 * Prescription/Procedures/Documents aren't separate sections here
 * because Lab ordering and Pharmacy prescribing already have their own
 * modules (this workspace doesn't duplicate them).
 */
export function ConsultationWorkspace() {
  const { id: visitId } = useParams<{ id: string }>();
  const hasPermission = useAuthStore((s) => s.hasPermission);

  const { data: visit } = useVisit(visitId);
  const { data: consultation } = useConsultationForVisit(visitId);
  const { data: vitalsList } = useVitalsForVisit(visitId);
  const { data: patientName } = usePatientName(visit?.patient);

  if (!visit || !consultation) {
    return <p>Loading…</p>;
  }

  const locked = consultation.locked_at !== null;

  return (
    <div className="consultation-workspace">
      <div className="invoice-header-card">
        <div className="card-row">
          <div>
            <p className="invoice-number">Consultation</p>
            <p className="invoice-patient">{patientName ?? "…"}</p>
          </div>
          <span className={pillClass(visit.status)}>{formatStatusLabel(visit.status)}</span>
        </div>
        <div className="invoice-totals-row" style={{ marginTop: "1rem" }}>
          {hasPermission("laboratory.lab_order.create") && (
            <Link to={`/laboratory/new?visit=${visit.id}`} className="button-primary inline-link">
              Order labs
            </Link>
          )}
          {hasPermission("pharmacy.prescription.create") && (
            <Link to={`/pharmacy/new?consultation=${consultation.id}`} className="button-primary inline-link">
              Prescribe
            </Link>
          )}
        </div>
      </div>

      <VitalsSection
        visitId={visit.id}
        vitals={vitalsList ?? []}
        canRecord={hasPermission("opd.vitals.create")}
      />

      <DraftSection consultation={consultation} locked={locked} canEdit={hasPermission("opd.consultation.update")} />

      <DiagnosisSection consultationId={consultation.id} locked={locked} canAdd={hasPermission("opd.diagnosis.create")} />

      {!locked && hasPermission("opd.consultation.complete") && (
        <CompleteButton visitId={visit.id} consultationId={consultation.id} />
      )}

      {locked && (
        <AddendumSection consultationId={consultation.id} canAdd={hasPermission("opd.addendum.create")} />
      )}
    </div>
  );
}

function VitalsSection({
  visitId,
  vitals,
  canRecord,
}: {
  visitId: string;
  vitals: { id: string; recorded_at: string; bp_systolic: number | null; bp_diastolic: number | null; pulse: number | null; temperature_c: string | null; spo2_percent: number | null }[];
  canRecord: boolean;
}) {
  const [form, setForm] = useState({
    bp_systolic: "",
    bp_diastolic: "",
    pulse: "",
    temperature_c: "",
    respiration_rate: "",
    spo2_percent: "",
  });
  const record = useRecordVitals(visitId);

  function field(name: keyof typeof form) {
    return {
      value: form[name],
      onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
        setForm((f) => ({ ...f, [name]: e.target.value })),
    };
  }

  async function submit() {
    const payload = Object.fromEntries(
      Object.entries(form)
        .filter(([, v]) => v !== "")
        .map(([k, v]) => [k, k === "temperature_c" ? v : Number(v)]),
    );
    await record.mutateAsync(payload);
    setForm({ bp_systolic: "", bp_diastolic: "", pulse: "", temperature_c: "", respiration_rate: "", spo2_percent: "" });
  }

  return (
    <section className="consult-section">
      <h2>Vitals</h2>
      {vitals.length === 0 && <p className="muted">No vitals recorded yet.</p>}
      {vitals.map((v) => (
        <div key={v.id} className="vitals-row">
          <span>BP {v.bp_systolic ?? "—"}/{v.bp_diastolic ?? "—"}</span>
          <span>Pulse {v.pulse ?? "—"}</span>
          <span>Temp {v.temperature_c ?? "—"}°C</span>
          <span>SpO2 {v.spo2_percent ?? "—"}%</span>
          <span className="muted">{new Date(v.recorded_at).toLocaleTimeString()}</span>
        </div>
      ))}

      {canRecord && (
        <div className="vitals-form">
          <input placeholder="BP systolic" {...field("bp_systolic")} />
          <input placeholder="BP diastolic" {...field("bp_diastolic")} />
          <input placeholder="Pulse" {...field("pulse")} />
          <input placeholder="Temp °C" {...field("temperature_c")} />
          <input placeholder="Resp rate" {...field("respiration_rate")} />
          <input placeholder="SpO2 %" {...field("spo2_percent")} />
          <button type="button" onClick={submit} disabled={record.isPending}>
            {record.isPending ? "Saving…" : "Record vitals"}
          </button>
        </div>
      )}
      {record.isError && <p className="form-error">{apiErrorMessage(record.error)}</p>}
    </section>
  );
}

function DraftSection({
  consultation,
  locked,
  canEdit,
}: {
  consultation: { id: string; chief_complaint: string; history_of_present_illness: string; examination_notes: string };
  locked: boolean;
  canEdit: boolean;
}) {
  const [values, setValues] = useState({
    chief_complaint: consultation.chief_complaint,
    history_of_present_illness: consultation.history_of_present_illness,
    examination_notes: consultation.examination_notes,
  });
  const update = useUpdateConsultationDraft(consultation.id);

  function save() {
    update.mutate(values);
  }

  return (
    <section className="consult-section">
      <h2>Clinical note {locked && <span className="muted">(locked)</span>}</h2>
      <label htmlFor="chief_complaint">Chief complaint</label>
      <textarea
        id="chief_complaint"
        disabled={locked || !canEdit}
        value={values.chief_complaint}
        onChange={(e) => setValues((v) => ({ ...v, chief_complaint: e.target.value }))}
        onBlur={save}
      />
      <label htmlFor="hpi">History of present illness</label>
      <textarea
        id="hpi"
        disabled={locked || !canEdit}
        value={values.history_of_present_illness}
        onChange={(e) => setValues((v) => ({ ...v, history_of_present_illness: e.target.value }))}
        onBlur={save}
      />
      <label htmlFor="examination">Examination notes</label>
      <textarea
        id="examination"
        disabled={locked || !canEdit}
        value={values.examination_notes}
        onChange={(e) => setValues((v) => ({ ...v, examination_notes: e.target.value }))}
        onBlur={save}
      />
      {update.isError && <p className="form-error">{apiErrorMessage(update.error)}</p>}
    </section>
  );
}

function DiagnosisSection({
  consultationId,
  locked,
  canAdd,
}: {
  consultationId: string;
  locked: boolean;
  canAdd: boolean;
}) {
  const { data: diagnoses } = useDiagnoses(consultationId);
  const addDiagnosis = useAddDiagnosis(consultationId);
  const [description, setDescription] = useState("");
  const [icdCode, setIcdCode] = useState("");
  const [type, setType] = useState<DiagnosisType>("primary");

  async function submit() {
    if (!description) return;
    await addDiagnosis.mutateAsync({ description, icd_code: icdCode, type });
    setDescription("");
    setIcdCode("");
  }

  return (
    <section className="consult-section">
      <h2>Diagnosis</h2>
      <ul className="diagnosis-list">
        {diagnoses?.map((d) => (
          <li key={d.id}>
            <strong>{d.icd_code || "—"}</strong> {d.description} <span className="muted">({d.type})</span>
          </li>
        ))}
        {diagnoses?.length === 0 && <li className="muted">No diagnosis recorded yet.</li>}
      </ul>

      {!locked && canAdd && (
        <div className="vitals-form">
          <input placeholder="ICD code" value={icdCode} onChange={(e) => setIcdCode(e.target.value)} />
          <input
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <select value={type} onChange={(e) => setType(e.target.value as DiagnosisType)}>
            <option value="primary">Primary</option>
            <option value="secondary">Secondary</option>
            <option value="differential">Differential</option>
          </select>
          <button type="button" onClick={submit} disabled={addDiagnosis.isPending}>
            Add diagnosis
          </button>
        </div>
      )}
      {addDiagnosis.isError && <p className="form-error">{apiErrorMessage(addDiagnosis.error)}</p>}
    </section>
  );
}

function CompleteButton({ visitId, consultationId }: { visitId: string; consultationId: string }) {
  const complete = useCompleteConsultation(visitId);
  return (
    <section className="consult-section">
      <button
        type="button"
        className="button-primary"
        onClick={() => complete.mutate(consultationId)}
        disabled={complete.isPending}
      >
        {complete.isPending ? "Completing…" : "Complete consultation"}
      </button>
      {complete.isError && <p className="form-error">{apiErrorMessage(complete.error)}</p>}
    </section>
  );
}

function AddendumSection({ consultationId, canAdd }: { consultationId: string; canAdd: boolean }) {
  const { data: addenda } = useAddenda(consultationId);
  const addAddendum = useAddAddendum(consultationId);
  const [text, setText] = useState("");

  async function submit() {
    if (!text) return;
    await addAddendum.mutateAsync(text);
    setText("");
  }

  return (
    <section className="consult-section">
      <h2>Addenda</h2>
      <ul className="diagnosis-list">
        {addenda?.map((a) => (
          <li key={a.id}>
            {a.text} <span className="muted">— {new Date(a.created_at).toLocaleString()}</span>
          </li>
        ))}
        {addenda?.length === 0 && <li className="muted">No addenda yet.</li>}
      </ul>
      {canAdd && (
        <div className="vitals-form">
          <input
            placeholder="Add a note (the consultation is locked — this is the only way to add more)"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button type="button" onClick={submit} disabled={addAddendum.isPending}>
            Add addendum
          </button>
        </div>
      )}
    </section>
  );
}
