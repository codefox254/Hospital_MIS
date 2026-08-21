import { ScrollView, StyleSheet, Text, View } from "react-native";

import { PlaceholderBanner } from "../components/PlaceholderBanner";
import { useCurrentUser } from "../lib/useCurrentUser";

export function HomeScreen() {
  const { user, loading } = useCurrentUser();

  return (
    <View style={styles.screen}>
      <PlaceholderBanner />
      <ScrollView contentContainerStyle={styles.content}>
        {loading ? (
          <Text>Loading...</Text>
        ) : (
          <>
            <Text style={styles.greeting}>Welcome, {user?.first_name ?? "there"}</Text>
            <Text style={styles.facility}>{user?.facility.name}</Text>

            <View style={styles.card}>
              <View style={styles.iconBadge}>
                <Text style={styles.iconGlyph}>{"\u{1F4C5}"}</Text>
              </View>
              <View style={styles.cardBody}>
                <Text style={styles.cardTitle}>Appointments</Text>
                <Text style={styles.cardSubtitle}>
                  See upcoming and past appointments in the Appointments tab.
                </Text>
              </View>
            </View>
            <View style={styles.card}>
              <View style={styles.iconBadge}>
                <Text style={styles.iconGlyph}>{"\u{1F9EA}"}</Text>
              </View>
              <View style={styles.cardBody}>
                <Text style={styles.cardTitle}>Lab results</Text>
                <Text style={styles.cardSubtitle}>
                  Track lab orders and their status in the Lab Results tab.
                </Text>
              </View>
            </View>
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#f5f5f5" },
  content: { padding: 16 },
  greeting: { fontSize: 26, fontWeight: "800", color: "#0f2c52" },
  facility: { fontSize: 14, color: "#6b7280", marginBottom: 20 },
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
  cardTitle: { fontSize: 16, fontWeight: "700", color: "#0f2c52", marginBottom: 2 },
  cardSubtitle: { fontSize: 13, color: "#6b7280" },
});
