import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { apiErrorMessage } from "../../lib/api";
import { useVisits } from "../opd/hooks";
import { useCreateLabOrder } from "./hooks";
import type { LabPriority } from "../../types/laboratory";

interface TestRow {
  test_code: string;
  test_name: string;
}

export function CreateLabOrderPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const presetVisit = searchParams.get("visit") ?? "";

  const [visitId, setVisitId] = useState(presetVisit);
  const [priority, setPriority] = useState<LabPriority>("routine");
  const [tests, setTests] = useState<TestRow[]>([{ test_code: "", test_name: "" }]);

  const { data: inProgressVisits } = useVisits("in_progress");
  const createOrder = useCreateLabOrder();

  function updateTest(index: number, field: keyof TestRow, value: string) {
    setTests((rows) => rows.map((row, i) => (i === index ? { ...row, [field]: value } : row)));
  }

  async function submit() {
    const items = tests.filter((t) => t.test_code && t.test_name);
    if (!visitId || items.length === 0) return;
    try {
      const order = await createOrder.mutateAsync({ visit: visitId, priority, items });
      navigate(`/laboratory/${order.id}`, { replace: true });
    } catch {
      // createOrder.error surfaces below.
    }
  }

  return (
    <div>
      <h1>Order lab tests</h1>
      <div className="form-grid booking-grid">
        <div>
          <label htmlFor="visit">Visit</label>
          {presetVisit ? (
            <input value={presetVisit} disabled />
          ) : (
            <select id="visit" value={visitId} onChange={(e) => setVisitId(e.target.value)}>
              <option value="">Select an active visit</option>
              {inProgressVisits?.results.map((v) => (
                <option key={v.id} value={v.id}>
                  Visit {v.id.slice(0, 8)} — checked in {new Date(v.checked_in_at).toLocaleString()}
                </option>
              ))}
            </select>
          )}
        </div>

        <div>
          <label htmlFor="priority">Priority</label>
          <select id="priority" value={priority} onChange={(e) => setPriority(e.target.value as LabPriority)}>
            <option value="routine">Routine</option>
            <option value="stat">Stat</option>
          </select>
        </div>

        <div className="checkbox-row" style={{ display: "block" }}>
          <label>Tests</label>
          {tests.map((row, i) => (
            <div key={i} className="vitals-form">
              <input
                placeholder="Test code (e.g. CBC)"
                value={row.test_code}
                onChange={(e) => updateTest(i, "test_code", e.target.value)}
              />
              <input
                placeholder="Test name"
                value={row.test_name}
                onChange={(e) => updateTest(i, "test_name", e.target.value)}
              />
            </div>
          ))}
          <button type="button" onClick={() => setTests((rows) => [...rows, { test_code: "", test_name: "" }])}>
            + Add another test
          </button>
        </div>

        {createOrder.isError && <p className="form-error">{apiErrorMessage(createOrder.error)}</p>}

        <button type="button" onClick={submit} disabled={createOrder.isPending}>
          {createOrder.isPending ? "Ordering…" : "Order tests"}
        </button>
      </div>
    </div>
  );
}
