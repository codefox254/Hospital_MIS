import { useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { api, apiErrorMessage } from "../lib/api";
import { departmentName, patientName, staffName, useLookups } from "../lib/useLookups";
import { formatLabel, statusStyle } from "../lib/statusStyle";
import type { Appointment } from "../types/appointment";
import type { AppointmentsStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<AppointmentsStackParamList, "AppointmentDetail">;

export function AppointmentDetailScreen({ route }: Props) {
  const { id } = route.params;
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lookupsReady = useLookups(appointment?.patient);

  useEffect(() => {
    api
      .get<Appointment>(`/appointments/appointments/${id}/`)
      .then(({ data }) => setAppointment(data))
      .catch((err) => setError(apiErrorMessage(err)));
  }, [id]);

  if (error) {
    return (
      <View style={styles.screen}>
        <Text style={styles.error}>{error}</Text>
      </View>
    );
  }

  if (!appointment || !lookupsReady) {
    return (
      <View style={styles.screen}>
        <Text style={styles.loading}>Loading...</Text>
      </View>
    );
  }

  const pill = statusStyle(appointment.status);
  const date = new Date(appointment.scheduled_at);

  return (
    <View style={styles.screen}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerCard}>
          <View style={[styles.pill, { backgroundColor: pill.bg }]}>
            <Text style={[styles.pillText, { color: pill.fg }]}>
              {formatLabel(appointment.status)}
            </Text>
          </View>
          <Text style={styles.dateMain}>
            {date.toLocaleDateString(undefined, {
              weekday: "long",
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </Text>
          <Text style={styles.dateTime}>
            {date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })} &middot;{" "}
            {appointment.duration_minutes} min
          </Text>
        </View>

        <DetailRow label="Patient" value={patientName(appointment.patient) || "—"} icon={"\u{1F464}"} />
        <DetailRow label="Doctor" value={staffName(appointment.doctor) || "—"} icon={"\u{1FA7A}"} />
        <DetailRow
          label="Department"
          value={departmentName(appointment.department) || "—"}
          icon={"\u{1F3E5}"}
        />
        <DetailRow
          label="Booking channel"
          value={formatLabel(appointment.booking_channel)}
          icon={"\u{1F4F1}"}
        />
      </ScrollView>
    </View>
  );
}

function DetailRow({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <View style={styles.card}>
      <View style={styles.iconBadge}>
        <Text style={styles.iconGlyph}>{icon}</Text>
      </View>
      <View style={styles.cardBody}>
        <Text style={styles.label}>{label}</Text>
        <Text style={styles.value}>{value}</Text>
      </View>
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
  dateMain: { color: "#fff", fontSize: 18, fontWeight: "700", marginTop: 10 },
  dateTime: { color: "#c7d3e3", fontSize: 14, marginTop: 4 },
  pill: { alignSelf: "flex-start", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  pillText: { fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
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
  label: { fontSize: 12, color: "#9ca3af", marginBottom: 2, fontWeight: "600" },
  value: { fontSize: 15, color: "#111827", fontWeight: "600" },
});
