import { useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { PlaceholderBanner } from "../components/PlaceholderBanner";
import { api, apiErrorMessage } from "../lib/api";
import { formatLabel, statusStyle } from "../lib/statusStyle";
import type { Invoice, Payment } from "../types/billing";
import type { PaginatedResponse } from "../types/appointment";
import type { BillingStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<BillingStackParamList, "InvoiceDetail">;

export function InvoiceDetailScreen({ route }: Props) {
  const { id } = route.params;
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Invoice>(`/billing/invoices/${id}/`)
      .then(({ data }) => setInvoice(data))
      .catch((err) => setError(apiErrorMessage(err)));
    api
      .get<PaginatedResponse<Payment>>(`/billing/payments/?invoice=${id}`)
      .then(({ data }) => setPayments(data.results))
      .catch(() => undefined);
  }, [id]);

  if (error) {
    return (
      <View style={styles.screen}>
        <PlaceholderBanner />
        <Text style={styles.error}>{error}</Text>
      </View>
    );
  }

  if (!invoice) {
    return (
      <View style={styles.screen}>
        <PlaceholderBanner />
        <Text style={styles.loading}>Loading...</Text>
      </View>
    );
  }

  const pill = statusStyle(invoice.status);

  return (
    <View style={styles.screen}>
      <PlaceholderBanner />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerCard}>
          <View style={styles.rowBetween}>
            <Text style={styles.invoiceNumber}>{invoice.invoice_number}</Text>
            <View style={[styles.pill, { backgroundColor: pill.bg }]}>
              <Text style={[styles.pillText, { color: pill.fg }]}>
                {formatLabel(invoice.status)}
              </Text>
            </View>
          </View>
          <View style={styles.totalsRow}>
            <View>
              <Text style={styles.totalsLabel}>Total</Text>
              <Text style={styles.totalsValue}>{invoice.total}</Text>
            </View>
            <View>
              <Text style={styles.totalsLabel}>Balance</Text>
              <Text style={styles.totalsValue}>{invoice.balance}</Text>
            </View>
          </View>
        </View>

        <Text style={styles.sectionTitle}>Line items</Text>
        {invoice.line_items.map((line) => (
          <View key={line.id} style={styles.lineCard}>
            <View style={styles.lineBody}>
              <Text style={styles.lineDescription}>{line.description}</Text>
              <Text style={styles.lineMeta}>
                {formatLabel(line.source_module)} &middot; Qty {line.quantity} &middot; @{" "}
                {line.unit_price}
              </Text>
            </View>
            <Text style={styles.lineAmount}>{line.amount}</Text>
          </View>
        ))}

        {payments.length > 0 ? (
          <>
            <Text style={styles.sectionTitle}>Payments</Text>
            {payments.map((payment) => {
              const paymentPill = statusStyle(payment.status);
              return (
                <View key={payment.id} style={styles.lineCard}>
                  <View style={styles.lineBody}>
                    <Text style={styles.lineDescription}>{formatLabel(payment.method)}</Text>
                    <Text style={styles.lineMeta}>
                      {new Date(payment.received_at).toLocaleString()}
                    </Text>
                  </View>
                  <View style={styles.paymentRight}>
                    <Text style={styles.lineAmount}>{payment.amount}</Text>
                    <View style={[styles.smallPill, { backgroundColor: paymentPill.bg }]}>
                      <Text style={[styles.smallPillText, { color: paymentPill.fg }]}>
                        {formatLabel(payment.status)}
                      </Text>
                    </View>
                  </View>
                </View>
              );
            })}
          </>
        ) : null}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#f5f5f5" },
  content: { padding: 16 },
  loading: { padding: 20, color: "#6b7280" },
  error: { padding: 20, color: "#b91c1c" },
  headerCard: { backgroundColor: "#0f2c52", borderRadius: 16, padding: 20, marginBottom: 16 },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  invoiceNumber: { color: "#fff", fontSize: 18, fontWeight: "700" },
  pill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  pillText: { fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
  totalsRow: { flexDirection: "row", gap: 32, marginTop: 16 },
  totalsLabel: { color: "#c7d3e3", fontSize: 12 },
  totalsValue: { color: "#fff", fontSize: 20, fontWeight: "800", marginTop: 2 },
  sectionTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#0f2c52",
    marginBottom: 8,
    marginTop: 4,
  },
  lineCard: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    shadowColor: "#0f2c52",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 1,
  },
  lineBody: { flex: 1, paddingRight: 10 },
  lineDescription: { fontSize: 14, fontWeight: "600", color: "#111827" },
  lineMeta: { fontSize: 12, color: "#9ca3af", marginTop: 2 },
  lineAmount: { fontSize: 14, fontWeight: "700", color: "#111827" },
  paymentRight: { alignItems: "flex-end", gap: 4 },
  smallPill: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999 },
  smallPillText: { fontSize: 10, fontWeight: "700", textTransform: "uppercase" },
});
