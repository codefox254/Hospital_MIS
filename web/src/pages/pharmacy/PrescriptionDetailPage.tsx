import { useState } from "react";
import { useParams } from "react-router-dom";

import { apiErrorMessage } from "../../lib/api";
import { useAuthStore } from "../../lib/auth-store";
import { usePatientName } from "../../lib/useLookups";
import { formatStatusLabel, pillClass } from "../../lib/statusPill";
import { useAllergyCheck, useDispense, useDrugs, usePrescription, useStockBatches } from "./hooks";
import type { PrescriptionItem } from "../../types/pharmacy";

export function PrescriptionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: prescription } = usePrescription(id);
  const { data: drugs } = useDrugs();
  const { data: batches } = useStockBatches();
  const { data: patientName } = usePatientName(prescription?.patient);

  if (!prescription) return <p>Loading…</p>;

  return (
    <div className="consultation-workspace">
      <div className="invoice-header-card">
        <div className="card-row">
          <div>
            <p className="invoice-number">Prescription</p>
            <p className="invoice-patient">{patientName ?? "…"}</p>
          </div>
          <span className={pillClass(prescription.status)}>
            {formatStatusLabel(prescription.status)}
          </span>
        </div>
      </div>

      {prescription.items.map((item) => (
        <DispenseCard
          key={item.id}
          patientId={prescription.patient}
          item={item}
          drugName={drugs?.find((d) => d.id === item.drug)?.name ?? item.drug}
          isControlled={drugs?.find((d) => d.id === item.drug)?.is_controlled ?? false}
          matchingBatches={batches?.filter((b) => b.drug === item.drug) ?? []}
        />
      ))}
    </div>
  );
}

function DispenseCard({
  patientId,
  item,
  drugName,
  isControlled,
  matchingBatches,
}: {
  patientId: string;
  item: PrescriptionItem;
  drugName: string;
  isControlled: boolean;
  matchingBatches: { id: string; batch_number: string; quantity_on_hand: number; expiry_date: string }[];
}) {
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const [batchId, setBatchId] = useState("");
  const [qty, setQty] = useState("");
  const { data: conflicts } = useAllergyCheck(patientId, item.drug);
  const dispense = useDispense(item.prescription);

  const canDispense =
    hasPermission("pharmacy.dispense_record.create") &&
    (!isControlled || hasPermission("pharmacy.dispense_record.create_controlled"));

  return (
    <section className="consult-section">
      <div className="modern-card" style={{ marginBottom: "0.75rem" }}>
        <div className="icon-badge">💊</div>
        <div className="card-body">
          <div className="card-row">
            <p className="card-title">{drugName}</p>
            {isControlled && <span className="pill pill-danger">Controlled</span>}
          </div>
          <p className="card-meta">
            {item.dosage}, {item.frequency}
            {item.duration_days ? ` for ${item.duration_days} days` : ""} · qty {item.qty_prescribed}
          </p>
        </div>
      </div>

      {conflicts && conflicts.length > 0 && (
        <p className="form-error">
          Allergy conflict: {conflicts.map((c) => `${c.substance} (${c.reaction})`).join(", ")}
        </p>
      )}

      {canDispense && (
        <div className="vitals-form">
          <select value={batchId} onChange={(e) => setBatchId(e.target.value)}>
            <option value="">Select a batch</option>
            {matchingBatches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.batch_number} ({b.quantity_on_hand} on hand, exp {b.expiry_date})
              </option>
            ))}
          </select>
          <input placeholder="Qty to dispense" value={qty} onChange={(e) => setQty(e.target.value)} />
          <button
            type="button"
            disabled={!batchId || !qty || dispense.isPending}
            onClick={() => dispense.mutate({ prescription_item: item.id, batch: batchId, qty_dispensed: Number(qty) })}
          >
            {dispense.isPending ? "Dispensing…" : "Confirm dispense"}
          </button>
        </div>
      )}
      {isControlled && !hasPermission("pharmacy.dispense_record.create_controlled") && (
        <p className="muted">Dispensing this controlled drug requires elevated permission.</p>
      )}
      {dispense.isError && <p className="form-error">{apiErrorMessage(dispense.error)}</p>}
      {dispense.isSuccess && <p className="muted">Dispensed successfully.</p>}
    </section>
  );
}
