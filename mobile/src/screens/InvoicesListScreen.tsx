import { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useNavigation } from "@react-navigation/native";

import { PlaceholderBanner } from "../components/PlaceholderBanner";
import { api, apiErrorMessage } from "../lib/api";
import { formatLabel, statusStyle } from "../lib/statusStyle";
import type { Invoice } from "../types/billing";
import type { PaginatedResponse } from "../types/appointment";
import type { BillingStackParamList } from "../navigation/types";

export function InvoicesListScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<BillingStackParamList>>();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const { data } = await api.get<PaginatedResponse<Invoice>>("/billing/invoices/");
      setInvoices(data.results);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <View style={styles.screen}>
      <PlaceholderBanner />
      <FlatList
        contentContainerStyle={styles.content}
        data={invoices}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}
        ListEmptyComponent={
          !loading ? <Text style={styles.empty}>{error ?? "No invoices found."}</Text> : undefined
        }
        renderItem={({ item }) => {
          const pill = statusStyle(item.status);
          return (
            <TouchableOpacity
              style={styles.card}
              onPress={() => navigation.navigate("InvoiceDetail", { id: item.id })}
            >
              <View style={styles.iconBadge}>
                <Text style={styles.iconGlyph}>{"\u{1F4B3}"}</Text>
              </View>
              <View style={styles.cardBody}>
                <View style={styles.rowBetween}>
                  <Text style={styles.invoiceNumber}>{item.invoice_number}</Text>
                  <View style={[styles.pill, { backgroundColor: pill.bg }]}>
                    <Text style={[styles.pillText, { color: pill.fg }]}>
                      {formatLabel(item.status)}
                    </Text>
                  </View>
                </View>
                <Text style={styles.total}>Total {item.total}</Text>
                <Text style={styles.balance}>Balance {item.balance}</Text>
              </View>
              <Text style={styles.chevron}>{"\u{1F441}"}</Text>
            </TouchableOpacity>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#f5f5f5" },
  content: { padding: 16 },
  empty: { textAlign: "center", color: "#6b7280", marginTop: 40 },
  card: {
    flexDirection: "row",
    alignItems: "center",
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
  iconBadge: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: "#eef2f9",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 14,
  },
  iconGlyph: { fontSize: 20 },
  cardBody: { flex: 1 },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  invoiceNumber: { fontSize: 15, fontWeight: "700", color: "#111827" },
  total: { fontSize: 13, color: "#374151", marginTop: 4 },
  balance: { fontSize: 12, color: "#9ca3af", marginTop: 2 },
  pill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  pillText: { fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
  chevron: { fontSize: 16, marginLeft: 8, opacity: 0.5 },
});
