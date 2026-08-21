import { StyleSheet, Text, View } from "react-native";

/**
 * FDO Health is spec'd as a patient-facing app, but the backend has no
 * patient identity/login yet (Consent.PORTAL_RELEASE anticipates a portal,
 * but no Patient<->auth link exists) — this screen is authenticating as a
 * staff account and showing facility-wide data as a stand-in until real
 * patient auth is built. Every data screen carries this banner so it's
 * never mistaken for the finished patient experience.
 */
export function PlaceholderBanner() {
  return (
    <View style={styles.banner}>
      <Text style={styles.text}>
        Placeholder: signed in with a staff account. Patient login isn't built yet — this shows
        facility data, not a personal patient view.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: "#fef3c7",
    borderBottomWidth: 1,
    borderBottomColor: "#fcd34d",
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  text: {
    color: "#92400e",
    fontSize: 12,
  },
});
