import { useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { PlaceholderBanner } from "../components/PlaceholderBanner";
import { api, apiErrorMessage } from "../lib/api";
import { staffName, useLookups } from "../lib/useLookups";
import { formatLabel, priorityStyle, statusStyle } from "../lib/statusStyle";
import type { LabOrder, LabResult, PaginatedResponse } from "../types/appointment";
import type { LabResultsStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<LabResultsStackParamList, "LabOrderDetail">;

export function LabOrderDetailScreen({ route }: Props) {
  const { id } = route.params;
  const [order, setOrder] = useState<LabOrder | null>(null);
  const [resultsByItem, setResultsByItem] = useState<Record<string, LabResult>>({});
  const [error, setError] = useState<string | null>(null);
  const lookupsReady = useLookups();

  useEffect(() => {
    api
      .get<LabOrder>(`/laboratory/lab-orders/${id}/`)
      .then(async ({ data }) => {
        setOrder(data);
        const entries = await Promise.all(
          data.items.map(async (item) => {
            const { data: page } = await api.get<PaginatedResponse<LabResult>>(
              `/laboratory/results/?lab_order_item=${item.id}`,
            );
            return [item.id, page.results[0]] as const;
          }),
        );
        const map: Record<string, LabResult> = {};
        entries.forEach(([itemId, result]) => {
          if (result) map[itemId] = result;
        });
        setResultsByItem(map);
      })
      .catch((err) => setError(apiErrorMessage(err)));
  }, [id]);

  if (error) {
    return (
      <View style={styles.screen}>
        <PlaceholderBanner />
        <Text style={styles.error}>{error}</Text>
      </View>
    );
  }

  if (!order || !lookupsReady) {
    return (
      <View style={styles.screen}>
        <PlaceholderBanner />
        <Text style={styles.loading}>Loading...</Text>
      </View>
    );
  }

  const statusPill = statusStyle(order.status);
  const priorityPill = priorityStyle(order.priority);

  return (
    <View style={styles.screen}>
      <PlaceholderBanner />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerCard}>
          <View style={styles.pillRow}>
            <View style={[styles.pill, { backgroundColor: statusPill.bg }]}>
              <Text style={[styles.pillText, { color: statusPill.fg }]}>
                {formatLabel(order.status)}
              </Text>
            </View>
            {order.priority !== "routine" ? (
              <View style={[styles.pill, { backgroundColor: priorityPill.bg }]}>
                <Text style={[styles.pillText, { color: priorityPill.fg }]}>
                  {formatLabel(order.priority)}
                </Text>
              </View>
            ) : null}
          </View>
          <Text style={styles.orderedAt}>
            Ordered {new Date(order.ordered_at).toLocaleString()}
          </Text>
          <Text style={styles.orderedBy}>by {staffName(order.ordered_by) || "—"}</Text>
        </View>

        {order.items.map((item) => {
          const result = resultsByItem[item.id];
          return (
            <View key={item.id} style={styles.itemCard}>
              <View style={styles.itemHeader}>
                <View style={styles.iconBadge}>
                  <Text style={styles.iconGlyph}>{"\u{1F9EA}"}</Text>
                </View>
                <View style={styles.itemHeaderText}>
                  <Text style={styles.testName}>{item.test_name}</Text>
                  <Text style={styles.testCode}>{item.test_code}</Text>
                </View>
                <View
                  style={[
                    styles.pill,
                    { backgroundColor: statusStyle(result ? result.status : "pending").bg },
                  ]}
                >
                  <Text
                    style={[
                      styles.pillText,
                      { color: statusStyle(result ? result.status : "pending").fg },
                    ]}
                  >
                    {result ? formatLabel(result.status) : "Queued"}
                  </Text>
                </View>
              </View>

              {result && result.values.length > 0 ? (
                <View style={styles.valuesTable}>
                  {result.values.map((v) => (
                    <View key={v.id} style={styles.valueRow}>
                      <Text style={styles.valueParam}>{v.parameter}</Text>
                      <Text
                        style={[
                          styles.valueNumber,
                          v.flag && v.flag !== "normal" ? styles.valueFlagged : null,
                        ]}
                      >
                        {v.value} {v.unit}
                      </Text>
                      <Text style={styles.valueRange}>{v.reference_range}</Text>
                    </View>
                  ))}
                </View>
              ) : (
                <Text style={styles.noResult}>
                  {result ? "No values recorded yet." : "Not yet collected/processed."}
                </Text>
              )}
            </View>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#f5f5f5" },
  content: { padding: 16 },
  loading: { padding: 20, color: "#6b7280" },
  error: { padding: 20, color: "#b91c1c" },
  headerCard: {
    backgroundColor: "#0f2c52",
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
  },
  pillRow: { flexDirection: "row", gap: 8 },
  pill: { alignSelf: "flex-start", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  pillText: { fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
  orderedAt: { color: "#fff", fontSize: 15, fontWeight: "700", marginTop: 10 },
  orderedBy: { color: "#c7d3e3", fontSize: 13, marginTop: 2 },
  itemCard: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    shadowColor: "#0f2c52",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 2,
  },
  itemHeader: { flexDirection: "row", alignItems: "center" },
  iconBadge: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: "#eef2f9",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  iconGlyph: { fontSize: 18 },
  itemHeaderText: { flex: 1 },
  testName: { fontSize: 15, fontWeight: "700", color: "#111827" },
  testCode: { fontSize: 12, color: "#9ca3af" },
  noResult: { fontSize: 13, color: "#9ca3af", marginTop: 10, fontStyle: "italic" },
  valuesTable: { marginTop: 12, borderTopWidth: 1, borderTopColor: "#f3f4f6", paddingTop: 10 },
  valueRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 4 },
  valueParam: { fontSize: 13, color: "#374151", flex: 1 },
  valueNumber: { fontSize: 13, fontWeight: "700", color: "#111827", flex: 1, textAlign: "center" },
  valueFlagged: { color: "#b91c1c" },
  valueRange: { fontSize: 12, color: "#9ca3af", flex: 1, textAlign: "right" },
});
