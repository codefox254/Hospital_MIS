import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { PlaceholderBanner } from "../components/PlaceholderBanner";
import { useAuthStore } from "../lib/auth-store";
import { useCurrentUser } from "../lib/useCurrentUser";

function initials(firstName: string, lastName: string): string {
  return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
}

export function ProfileScreen() {
  const { user, loading } = useCurrentUser();
  const logout = useAuthStore((s) => s.logout);

  return (
    <View style={styles.screen}>
      <PlaceholderBanner />
      <ScrollView contentContainerStyle={styles.content}>
        {loading || !user ? (
          <Text>Loading...</Text>
        ) : (
          <>
            <View style={styles.identity}>
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>{initials(user.first_name, user.last_name)}</Text>
              </View>
              <View>
                <Text style={styles.name}>
                  {user.first_name} {user.last_name}
                </Text>
                <Text style={styles.email}>{user.email}</Text>
              </View>
            </View>

            <View style={styles.card}>
              <View style={styles.iconBadge}>
                <Text style={styles.iconGlyph}>{"\u{1F3E5}"}</Text>
              </View>
              <View style={styles.cardBody}>
                <Text style={styles.label}>Facility</Text>
                <Text style={styles.value}>
                  {user.facility.name} ({user.facility.code})
                </Text>
              </View>
            </View>
            <View style={styles.card}>
              <View style={styles.iconBadge}>
                <Text style={styles.iconGlyph}>{"\u{1F510}"}</Text>
              </View>
              <View style={styles.cardBody}>
                <Text style={styles.label}>MFA</Text>
                <Text style={styles.value}>{user.mfa_enabled ? "Enabled" : "Not enabled"}</Text>
              </View>
            </View>

            <TouchableOpacity style={styles.signOut} onPress={logout}>
              <Text style={styles.signOutText}>Sign out</Text>
            </TouchableOpacity>
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#f5f5f5" },
  content: { padding: 16 },
  identity: { flexDirection: "row", alignItems: "center", marginBottom: 24 },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#0f2c52",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 14,
  },
  avatarText: { color: "#fff", fontSize: 20, fontWeight: "700" },
  name: { fontSize: 20, fontWeight: "800", color: "#0f2c52" },
  email: { fontSize: 13, color: "#6b7280", marginTop: 2 },
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
  signOut: {
    marginTop: 12,
    backgroundColor: "#b91c1c",
    borderRadius: 14,
    paddingVertical: 15,
    alignItems: "center",
    shadowColor: "#b91c1c",
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 3,
  },
  signOutText: { color: "#fff", fontSize: 16, fontWeight: "700" },
});
