import { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";

import { PlaceholderBanner } from "../components/PlaceholderBanner";
import { api, apiErrorMessage } from "../lib/api";
import { formatLabel, statusStyle } from "../lib/statusStyle";
import type { Appointment, PaginatedResponse } from "../types/appointment";

export function AppointmentsScreen() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const { data } = await api.get<PaginatedResponse<Appointment>>("/appointments/appointments/");
      setAppointments(data.results);
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
        data={appointments}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}
        ListEmptyComponent={
          !loading ? (
            <Text style={styles.empty}>{error ?? "No appointments found."}</Text>
          ) : undefined
        }
        renderItem={({ item }) => {
          const pill = statusStyle(item.status);
          const date = new Date(item.scheduled_at);
          return (
            <View style={styles.card}>
              <View style={styles.iconBadge}>
                <Text style={styles.iconGlyph}>{"\u{1F4C5}"}</Text>
              </View>
              <View style={styles.cardBody}>
                <View style={styles.rowBetween}>
                  <Text style={styles.dateMain}>
                    {date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}
                  </Text>
                  <View style={[styles.pill, { backgroundColor: pill.bg }]}>
                    <Text style={[styles.pillText, { color: pill.fg }]}>
                      {formatLabel(item.status)}
                    </Text>
                  </View>
                </View>
                <Text style={styles.dateTime}>
                  {date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
                </Text>
                <Text style={styles.meta}>
                  {item.duration_minutes} min &middot; {formatLabel(item.booking_channel)}
                </Text>
              </View>
            </View>
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
  dateMain: { fontSize: 15, fontWeight: "700", color: "#111827" },
  dateTime: { fontSize: 13, color: "#374151", marginTop: 2 },
  meta: { fontSize: 12, color: "#9ca3af", marginTop: 6 },
  pill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  pillText: { fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
});
