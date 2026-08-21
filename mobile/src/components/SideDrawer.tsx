import { useEffect, useRef } from "react";
import {
  Animated,
  Dimensions,
  Pressable,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import type { CurrentUser } from "../types/auth";

const DRAWER_WIDTH = Math.min(300, Dimensions.get("window").width * 0.8);

interface NavItem {
  key: string;
  label: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { key: "Home", label: "Home", icon: "\u{1F3E0}" },
  { key: "Appointments", label: "Appointments", icon: "\u{1F4C5}" },
  { key: "Lab Results", label: "Lab Results", icon: "\u{1F9EA}" },
  { key: "Billing", label: "Billing", icon: "\u{1F4B3}" },
  { key: "Profile", label: "Profile", icon: "\u{1F464}" },
];

function initials(firstName?: string, lastName?: string): string {
  return `${firstName?.charAt(0) ?? ""}${lastName?.charAt(0) ?? ""}`.toUpperCase();
}

interface Props {
  visible: boolean;
  activeRoute: string;
  user: CurrentUser | null;
  onNavigate: (route: string) => void;
  onSignOut: () => void;
  onClose: () => void;
}

export function SideDrawer({ visible, activeRoute, user, onNavigate, onSignOut, onClose }: Props) {
  const translateX = useRef(new Animated.Value(-DRAWER_WIDTH)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(translateX, {
        toValue: visible ? 0 : -DRAWER_WIDTH,
        duration: 220,
        useNativeDriver: true,
      }),
      Animated.timing(backdropOpacity, {
        toValue: visible ? 1 : 0,
        duration: 220,
        useNativeDriver: true,
      }),
    ]).start();
  }, [visible, translateX, backdropOpacity]);

  if (!visible) {
    // Keep mounted while animating out would need extra state; since the
    // close animation is short and this is a simple nav drawer (not a
    // gesture-driven one), unmounting once closed is simpler and avoids an
    // invisible-but-touchable panel lingering off-screen.
    return null;
  }

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      <Animated.View
        style={[styles.backdrop, { opacity: backdropOpacity }]}
        pointerEvents={visible ? "auto" : "none"}
      >
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
      </Animated.View>

      <Animated.View style={[styles.drawer, { transform: [{ translateX }] }]}>
        <View style={styles.header}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{initials(user?.first_name, user?.last_name)}</Text>
          </View>
          <Text style={styles.name}>
            {user ? `${user.first_name} ${user.last_name}` : "..."}
          </Text>
          <Text style={styles.facility}>{user?.facility.name}</Text>
        </View>

        <View style={styles.navList}>
          {NAV_ITEMS.map((item) => {
            const active = item.key === activeRoute;
            return (
              <TouchableOpacity
                key={item.key}
                style={[styles.navItem, active ? styles.navItemActive : null]}
                onPress={() => onNavigate(item.key)}
              >
                <Text style={styles.navIcon}>{item.icon}</Text>
                <Text style={[styles.navLabel, active ? styles.navLabelActive : null]}>
                  {item.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <TouchableOpacity style={styles.signOut} onPress={onSignOut}>
          <Text style={styles.signOutText}>Sign out</Text>
        </TouchableOpacity>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(15, 44, 82, 0.4)",
  },
  drawer: {
    position: "absolute",
    top: 0,
    bottom: 0,
    left: 0,
    width: DRAWER_WIDTH,
    backgroundColor: "#0f2c52",
    paddingTop: 56,
    paddingHorizontal: 20,
  },
  header: {
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255,255,255,0.15)",
    paddingBottom: 20,
    marginBottom: 16,
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: "rgba(255,255,255,0.15)",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 10,
  },
  avatarText: { color: "#fff", fontSize: 18, fontWeight: "700" },
  name: { color: "#fff", fontSize: 17, fontWeight: "700" },
  facility: { color: "#c7d3e3", fontSize: 12, marginTop: 2 },
  navList: { flex: 1 },
  navItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    paddingHorizontal: 10,
    borderRadius: 10,
    marginBottom: 4,
  },
  navItemActive: { backgroundColor: "rgba(255,255,255,0.12)" },
  navIcon: { fontSize: 18, marginRight: 14 },
  navLabel: { color: "#c7d3e3", fontSize: 15, fontWeight: "600" },
  navLabelActive: { color: "#fff" },
  signOut: {
    borderTopWidth: 1,
    borderTopColor: "rgba(255,255,255,0.15)",
    paddingVertical: 18,
  },
  signOutText: { color: "#fca5a5", fontSize: 15, fontWeight: "700" },
});
