import http from "k6/http";
import { check } from "k6";

const targetUrl = __ENV.TARGET_URL || "http://fraud-api:8000";
const payload = JSON.stringify({
  transaction_id: "TXN-2026-00042",
  amount_sar: 150.0,
  channel: "ecom",
  merchant_category: "ELECTRONICS",
  customer_id: "CUST-0042",
  timestamp: "2026-07-05T22:14:00Z",
});

export default function () {
  const response = http.post(`${targetUrl}/v1/predict`, payload, {
    headers: { "Content-Type": "application/json" },
  });

  check(response, {
    "returns 200": (result) => result.status === 200,
    "returns prediction contract": (result) => {
      const body = result.json();
      return body.transaction_id && body.decision && body.model_version && body.trace_id;
    },
  });
}
