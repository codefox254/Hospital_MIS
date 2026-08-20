import { useState } from "react";
import { useParams } from "react-router-dom";

import { apiErrorMessage } from "../../lib/api";
import { useAuthStore } from "../../lib/auth-store";
import {
  useCollectSample,
  useEnterResult,
  useLabOrder,
  useResultsForOrder,
  useSamplesForOrder,
  useVerifyResult,
} from "./hooks";
import type { LabOrderItem, ResultFlag } from "../../types/laboratory";

export function LabOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: order } = useLabOrder(id);
  const { data: samples } = useSamplesForOrder(id ?? "");
  const { data: results } = useResultsForOrder(id ?? "");

  if (!order) return <p>Loading…</p>;

  return (
    <div className="consultation-workspace">
      <div className="page-header">
        <h1>Lab order</h1>
        <span className={`status-pill status-${order.status}`}>{order.status}</span>
      </div>

      {order.items.map((item) => (
        <LabItemCard
          key={item.id}
          orderId={order.id}
          item={item}
          sample={samples?.[item.id] ?? null}
          result={results?.[item.id] ?? null}
        />
      ))}
    </div>
  );
}

function LabItemCard({
  orderId,
  item,
  sample,
  result,
}: {
  orderId: string;
  item: LabOrderItem;
  sample: { id: string; barcode: string; status: string } | null;
  result: {
    id: string;
    status: string;
    is_critical: boolean;
    values: { parameter: string; value: string; unit: string; flag: string }[];
  } | null;
}) {
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const [barcode, setBarcode] = useState("");
  const [parameter, setParameter] = useState("");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("");
  const [flag, setFlag] = useState<ResultFlag>("normal");

  const collect = useCollectSample(orderId);
  const enterResult = useEnterResult(orderId);
  const verify = useVerifyResult(orderId);

  return (
    <section className="consult-section">
      <h2>
        {item.test_code} — {item.test_name}
      </h2>

      {!sample && hasPermission("laboratory.lab_sample.create") && (
        <div className="vitals-form">
          <input placeholder="Barcode" value={barcode} onChange={(e) => setBarcode(e.target.value)} />
          <button
            type="button"
            disabled={!barcode || collect.isPending}
            onClick={() => collect.mutate({ itemId: item.id, barcode })}
          >
            Collect sample
          </button>
        </div>
      )}
      {sample && (
        <p className="muted">
          Sample {sample.barcode} — {sample.status}
        </p>
      )}
      {collect.isError && <p className="form-error">{apiErrorMessage(collect.error)}</p>}

      {sample && !result && hasPermission("laboratory.lab_result.create") && (
        <div className="vitals-form">
          <input placeholder="Parameter" value={parameter} onChange={(e) => setParameter(e.target.value)} />
          <input placeholder="Value" value={value} onChange={(e) => setValue(e.target.value)} />
          <input placeholder="Unit" value={unit} onChange={(e) => setUnit(e.target.value)} />
          <select value={flag} onChange={(e) => setFlag(e.target.value as ResultFlag)}>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <button
            type="button"
            disabled={!parameter || !value || enterResult.isPending}
            onClick={() => enterResult.mutate({ itemId: item.id, parameter, value, unit, flag })}
          >
            Enter result
          </button>
        </div>
      )}
      {enterResult.isError && <p className="form-error">{apiErrorMessage(enterResult.error)}</p>}

      {result && (
        <div>
          <ul className="diagnosis-list">
            {result.values.map((v, i) => (
              <li key={i}>
                {v.parameter}: {v.value} {v.unit}{" "}
                {v.flag !== "normal" && <span className={`priority-${v.flag === "critical" ? "emergency" : "priority"}`}>({v.flag})</span>}
              </li>
            ))}
          </ul>
          <p className="muted">
            Status: {result.status}
            {result.is_critical && " — CRITICAL"}
          </p>
          {result.status === "entered" && hasPermission("laboratory.lab_result.verify") && (
            <button type="button" onClick={() => verify.mutate(result.id)} disabled={verify.isPending}>
              {verify.isPending ? "Verifying…" : "Verify result"}
            </button>
          )}
          {verify.isError && <p className="form-error">{apiErrorMessage(verify.error)}</p>}
        </div>
      )}
    </section>
  );
}
