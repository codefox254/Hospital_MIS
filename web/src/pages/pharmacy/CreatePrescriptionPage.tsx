import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { apiErrorMessage } from "../../lib/api";
import { useCreatePrescription, useDrugs } from "./hooks";

interface ItemRow {
  drug: string;
  dosage: string;
  frequency: string;
  duration_days: string;
  qty_prescribed: string;
}

const emptyRow: ItemRow = { drug: "", dosage: "", frequency: "", duration_days: "", qty_prescribed: "" };

export function CreatePrescriptionPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const consultationId = searchParams.get("consultation") ?? "";

  const { data: drugs } = useDrugs();
  const createPrescription = useCreatePrescription();
  const [rows, setRows] = useState<ItemRow[]>([{ ...emptyRow }]);

  function updateRow(index: number, field: keyof ItemRow, value: string) {
    setRows((r) => r.map((row, i) => (i === index ? { ...row, [field]: value } : row)));
  }

  async function submit() {
    const items = rows
      .filter((r) => r.drug && r.dosage && r.frequency && r.qty_prescribed)
      .map((r) => ({
        drug: r.drug,
        dosage: r.dosage,
        frequency: r.frequency,
        duration_days: r.duration_days ? Number(r.duration_days) : undefined,
        qty_prescribed: Number(r.qty_prescribed),
      }));
    if (!consultationId || items.length === 0) return;
    try {
      const prescription = await createPrescription.mutateAsync({ consultation: consultationId, items });
      navigate(`/pharmacy/${prescription.id}`, { replace: true });
    } catch {
      // createPrescription.error surfaces below.
    }
  }

  if (!consultationId) {
    return (
      <p className="form-error">
        No consultation selected — prescribe from the OPD consultation workspace's "Prescribe" link.
      </p>
    );
  }

  return (
    <div>
      <h1>Prescribe</h1>
      <div className="form-grid booking-grid">
        {rows.map((row, i) => (
          <div key={i} className="checkbox-row" style={{ display: "block" }}>
            <label>Item {i + 1}</label>
            <div className="vitals-form">
              <select value={row.drug} onChange={(e) => updateRow(i, "drug", e.target.value)}>
                <option value="">Select a drug</option>
                {drugs?.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} {d.strength}
                    {d.is_controlled ? " (controlled)" : ""}
                  </option>
                ))}
              </select>
              <input
                placeholder="Dosage (e.g. 1 tablet)"
                value={row.dosage}
                onChange={(e) => updateRow(i, "dosage", e.target.value)}
              />
              <input
                placeholder="Frequency (e.g. twice daily)"
                value={row.frequency}
                onChange={(e) => updateRow(i, "frequency", e.target.value)}
              />
              <input
                placeholder="Duration (days)"
                value={row.duration_days}
                onChange={(e) => updateRow(i, "duration_days", e.target.value)}
              />
              <input
                placeholder="Qty prescribed"
                value={row.qty_prescribed}
                onChange={(e) => updateRow(i, "qty_prescribed", e.target.value)}
              />
            </div>
          </div>
        ))}
        <button type="button" onClick={() => setRows((r) => [...r, { ...emptyRow }])}>
          + Add another item
        </button>

        {createPrescription.isError && (
          <p className="form-error">{apiErrorMessage(createPrescription.error)}</p>
        )}

        <button type="button" onClick={submit} disabled={createPrescription.isPending}>
          {createPrescription.isPending ? "Prescribing…" : "Prescribe"}
        </button>
      </div>
    </div>
  );
}
