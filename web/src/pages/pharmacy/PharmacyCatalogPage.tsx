import { useState } from "react";

import { apiErrorMessage } from "../../lib/api";
import { useAuthStore } from "../../lib/auth-store";
import { useCreateDrug, useCreateStockBatch, useDrugs, useStockBatches } from "./hooks";

const LOW_STOCK_THRESHOLD = 10;
const EXPIRY_WARNING_DAYS = 30;

function expiryPill(expiryDate: string): { className: string; label: string } {
  const days = Math.ceil(
    (new Date(expiryDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24),
  );
  if (days < 0) return { className: "pill pill-danger", label: "Expired" };
  if (days <= EXPIRY_WARNING_DAYS) return { className: "pill pill-warning", label: `${days}d left` };
  return { className: "pill pill-success", label: "OK" };
}

export function PharmacyCatalogPage() {
  const { data: drugs } = useDrugs();
  const { data: batches } = useStockBatches();
  const hasPermission = useAuthStore((s) => s.hasPermission);

  const [drugName, setDrugName] = useState("");
  const [drugStrength, setDrugStrength] = useState("");
  const [drugForm, setDrugForm] = useState("");
  const [isControlled, setIsControlled] = useState(false);
  const createDrug = useCreateDrug();

  const [batchDrug, setBatchDrug] = useState("");
  const [batchNumber, setBatchNumber] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitCost, setUnitCost] = useState("");
  const createBatch = useCreateStockBatch();

  const stockByDrug = new Map<string, number>();
  batches?.forEach((b) => {
    stockByDrug.set(b.drug, (stockByDrug.get(b.drug) ?? 0) + b.quantity_on_hand);
  });

  return (
    <div>
      <h1>Drugs &amp; stock</h1>

      <h2 className="section-title">Drug catalog</h2>
      <div className="card-list">
        {drugs?.length === 0 && <p className="card-subtitle">No drugs in the catalog yet.</p>}
        {drugs?.map((d) => {
          const stock = stockByDrug.get(d.id) ?? 0;
          return (
            <div key={d.id} className="modern-card">
              <div className="icon-badge">💊</div>
              <div className="card-body">
                <div className="card-row">
                  <p className="card-title">
                    {d.name} {d.strength}
                  </p>
                  <div style={{ display: "flex", gap: "0.4rem" }}>
                    {d.is_controlled && <span className="pill pill-danger">Controlled</span>}
                    {stock <= LOW_STOCK_THRESHOLD && (
                      <span className="pill pill-warning">Low stock</span>
                    )}
                  </div>
                </div>
                <p className="card-meta">
                  {d.form} · {d.generic_name || "—"} · {stock} on hand
                </p>
              </div>
            </div>
          );
        })}
      </div>
      {hasPermission("pharmacy.drug.create") && (
        <div className="form-panel">
          <h3>Add drug</h3>
          <input placeholder="Name" value={drugName} onChange={(e) => setDrugName(e.target.value)} />
          <input
            placeholder="Strength (e.g. 500mg)"
            value={drugStrength}
            onChange={(e) => setDrugStrength(e.target.value)}
            style={{ marginTop: "0.5rem" }}
          />
          <input
            placeholder="Form (e.g. tablet)"
            value={drugForm}
            onChange={(e) => setDrugForm(e.target.value)}
            style={{ marginTop: "0.5rem" }}
          />
          <label className="checkbox-row" style={{ width: "auto", marginTop: "0.5rem" }}>
            <input type="checkbox" checked={isControlled} onChange={(e) => setIsControlled(e.target.checked)} />
            Controlled
          </label>
          <button
            type="button"
            className="button-primary"
            disabled={!drugName || createDrug.isPending}
            onClick={() =>
              createDrug.mutate(
                { name: drugName, generic_name: "", strength: drugStrength, form: drugForm, is_controlled: isControlled },
                {
                  onSuccess: () => {
                    setDrugName("");
                    setDrugStrength("");
                    setDrugForm("");
                    setIsControlled(false);
                  },
                },
              )
            }
          >
            Add drug
          </button>
          {createDrug.isError && <p className="form-error">{apiErrorMessage(createDrug.error)}</p>}
        </div>
      )}

      <h2 className="section-title">Stock batches</h2>
      <div className="card-list">
        {batches?.length === 0 && <p className="card-subtitle">No stock batches yet.</p>}
        {batches?.map((b) => {
          const pill = expiryPill(b.expiry_date);
          return (
            <div key={b.id} className="modern-card">
              <div className="icon-badge">📦</div>
              <div className="card-body">
                <div className="card-row">
                  <p className="card-title">{drugs?.find((d) => d.id === b.drug)?.name ?? b.drug}</p>
                  <span className={pill.className}>{pill.label}</span>
                </div>
                <p className="card-meta">
                  Batch {b.batch_number} · {b.quantity_on_hand} on hand · expires {b.expiry_date}
                  {b.unit_cost ? ` · @ ${b.unit_cost}` : ""}
                </p>
              </div>
            </div>
          );
        })}
      </div>
      {hasPermission("pharmacy.stock_batch.create") && (
        <div className="form-panel">
          <h3>Receive stock batch</h3>
          <select value={batchDrug} onChange={(e) => setBatchDrug(e.target.value)}>
            <option value="">Select a drug</option>
            {drugs?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} {d.strength}
              </option>
            ))}
          </select>
          <label htmlFor="batch-number">Batch number</label>
          <input id="batch-number" value={batchNumber} onChange={(e) => setBatchNumber(e.target.value)} />
          <label htmlFor="batch-expiry">Expiry date</label>
          <input id="batch-expiry" type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
          <label htmlFor="batch-qty">Quantity</label>
          <input id="batch-qty" placeholder="Quantity" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          <label htmlFor="batch-cost">Unit cost</label>
          <input id="batch-cost" placeholder="Unit cost" value={unitCost} onChange={(e) => setUnitCost(e.target.value)} />
          <button
            type="button"
            className="button-primary"
            disabled={!batchDrug || !batchNumber || !expiryDate || !quantity || createBatch.isPending}
            onClick={() =>
              createBatch.mutate(
                {
                  drug: batchDrug,
                  batch_number: batchNumber,
                  expiry_date: expiryDate,
                  quantity_on_hand: Number(quantity),
                  unit_cost: unitCost || null,
                },
                {
                  onSuccess: () => {
                    setBatchDrug("");
                    setBatchNumber("");
                    setExpiryDate("");
                    setQuantity("");
                    setUnitCost("");
                  },
                },
              )
            }
          >
            Add batch
          </button>
          {createBatch.isError && <p className="form-error">{apiErrorMessage(createBatch.error)}</p>}
        </div>
      )}
    </div>
  );
}
