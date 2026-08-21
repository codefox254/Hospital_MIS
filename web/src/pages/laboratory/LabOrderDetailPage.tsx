import { useState } from "react";
import { useParams } from "react-router-dom";

import { apiErrorMessage } from "../../lib/api";
import { useAuthStore } from "../../lib/auth-store";
import { formatStatusLabel, pillClass } from "../../lib/statusPill";
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
      <div className="invoice-header-card">
        <div className="card-row">
          <div>
            <p className="invoice-number">Lab order</p>
            <p className="invoice-patient">
              {order.priority !== "routine" ? formatStatusLabel(order.priority) + " · " : ""}
              {new Date(order.ordered_at).toLocaleString()}
            </p>
          </div>
          <span className={pillClass(order.status)}>{formatStatusLabel(order.status)}</span>
        </div>
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
      <div className="modern-card" style={{ marginBottom: sample || result ? "0.75rem" : 0 }}>
        <div className="icon-badge">🧪</div>
        <div className="card-body">
          <div className="card-row">
            <p className="card-title">{item.test_name}</p>
            {sample && <span className={pillClass(sample.status)}>{formatStatusLabel(sample.status)}</span>}
          </div>
          <p className="card-meta">
            {item.test_code}
            {sample ? ` · Sample ${sample.barcode}` : ""}
          </p>
        </div>
      </div>

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
        <div className="modern-card" style={{ marginTop: "0.75rem" }}>
          <div className="card-body">
            <div className="card-row">
              <p className="card-title">Result</p>
              <div style={{ display: "flex", gap: "0.4rem" }}>
                {result.is_critical && <span className="pill pill-danger">Critical</span>}
                <span className={pillClass(result.status)}>{formatStatusLabel(result.status)}</span>
              </div>
            </div>
            <div style={{ marginTop: "0.6rem" }}>
              {result.values.map((v, i) => (
                <div key={i} className="receipt-row">
                  <span>{v.parameter}</span>
                  <span>
                    {v.value} {v.unit}{" "}
                    {v.flag !== "normal" && (
                      <span className={v.flag === "critical" ? "pill pill-danger" : "pill pill-warning"}>
                        {v.flag}
                      </span>
                    )}
                  </span>
                </div>
              ))}
            </div>
            {result.status === "entered" && hasPermission("laboratory.lab_result.verify") && (
              <button
                type="button"
                className="button-primary"
                style={{ marginTop: "0.75rem" }}
                onClick={() => verify.mutate(result.id)}
                disabled={verify.isPending}
              >
                {verify.isPending ? "Verifying…" : "Verify result"}
              </button>
            )}
            {verify.isError && <p className="form-error">{apiErrorMessage(verify.error)}</p>}
          </div>
        </div>
      )}
    </section>
  );
}
