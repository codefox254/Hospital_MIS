import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Text } from "react-native";

import { useAuthStore } from "../lib/auth-store";
import { LoginScreen } from "../screens/LoginScreen";
import { HomeScreen } from "../screens/HomeScreen";
import { AppointmentsScreen } from "../screens/AppointmentsScreen";
import { LabResultsScreen } from "../screens/LabResultsScreen";
import { ProfileScreen } from "../screens/ProfileScreen";

const Tab = createBottomTabNavigator();

const TAB_ICONS: Record<string, string> = {
  Home: "\u{1F3E0}",
  Appointments: "\u{1F4C5}",
  "Lab Results": "\u{1F9EA}",
  Profile: "\u{1F464}",
};

function TabIcon({ route, focused }: { route: string; focused: boolean }) {
  return (
    <Text style={{ fontSize: 22, opacity: focused ? 1 : 0.45 }}>{TAB_ICONS[route]}</Text>
  );
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerStyle: { backgroundColor: "#0f2c52" },
        headerTintColor: "#fff",
        headerTitleStyle: { fontWeight: "700" },
        tabBarActiveTintColor: "#0f2c52",
        tabBarInactiveTintColor: "#9ca3af",
        tabBarLabelStyle: { fontSize: 12, fontWeight: "600" },
        tabBarStyle: { height: 62, paddingBottom: 8, paddingTop: 6 },
        tabBarIcon: ({ focused }) => <TabIcon route={route.name} focused={focused} />,
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Appointments" component={AppointmentsScreen} />
      <Tab.Screen name="Lab Results" component={LabResultsScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

export function RootNavigator() {
  const access = useAuthStore((s) => s.access);

  return (
    <NavigationContainer>{access ? <MainTabs /> : <LoginScreen />}</NavigationContainer>
  );
}
