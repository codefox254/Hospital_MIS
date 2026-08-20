import { useState } from "react";

import { apiErrorMessage } from "../../lib/api";
import { useAuthStore } from "../../lib/auth-store";
import { useCreateDrug, useCreateStockBatch, useDrugs, useStockBatches } from "./hooks";

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

  return (
    <div>
      <h1>Drugs &amp; stock</h1>

      <section className="consult-section">
        <h2>Drug catalog</h2>
        <ul className="diagnosis-list">
          {drugs?.map((d) => (
            <li key={d.id}>
              {d.name} {d.strength} ({d.form}) {d.is_controlled && <span className="priority-priority">controlled</span>}
            </li>
          ))}
        </ul>
        {hasPermission("pharmacy.drug.create") && (
          <div className="vitals-form">
            <input placeholder="Name" value={drugName} onChange={(e) => setDrugName(e.target.value)} />
            <input placeholder="Strength (e.g. 500mg)" value={drugStrength} onChange={(e) => setDrugStrength(e.target.value)} />
            <input placeholder="Form (e.g. tablet)" value={drugForm} onChange={(e) => setDrugForm(e.target.value)} />
            <label className="checkbox-row" style={{ width: "auto" }}>
              <input type="checkbox" checked={isControlled} onChange={(e) => setIsControlled(e.target.checked)} />
              Controlled
            </label>
            <button
              type="button"
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
          </div>
        )}
        {createDrug.isError && <p className="form-error">{apiErrorMessage(createDrug.error)}</p>}
      </section>

      <section className="consult-section">
        <h2>Stock batches</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>Drug</th>
              <th>Batch</th>
              <th>Qty on hand</th>
              <th>Expiry</th>
            </tr>
          </thead>
          <tbody>
            {batches?.map((b) => (
              <tr key={b.id}>
                <td>{drugs?.find((d) => d.id === b.drug)?.name ?? b.drug}</td>
                <td>{b.batch_number}</td>
                <td>{b.quantity_on_hand}</td>
                <td>{b.expiry_date}</td>
              </tr>
            ))}
            {batches?.length === 0 && (
              <tr>
                <td colSpan={4}>No stock batches yet.</td>
              </tr>
            )}
          </tbody>
        </table>

        {hasPermission("pharmacy.stock_batch.create") && (
          <div className="vitals-form">
            <select value={batchDrug} onChange={(e) => setBatchDrug(e.target.value)}>
              <option value="">Select a drug</option>
              {drugs?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} {d.strength}
                </option>
              ))}
            </select>
            <input placeholder="Batch number" value={batchNumber} onChange={(e) => setBatchNumber(e.target.value)} />
            <input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
            <input placeholder="Quantity" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
            <input placeholder="Unit cost" value={unitCost} onChange={(e) => setUnitCost(e.target.value)} />
            <button
              type="button"
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
          </div>
        )}
        {createBatch.isError && <p className="form-error">{apiErrorMessage(createBatch.error)}</p>}
      </section>
    </div>
  );
}
