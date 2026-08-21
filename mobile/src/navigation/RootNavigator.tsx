import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { Text } from "react-native";

import { useAuthStore } from "../lib/auth-store";
import { LoginScreen } from "../screens/LoginScreen";
import { HomeScreen } from "../screens/HomeScreen";
import { AppointmentsScreen } from "../screens/AppointmentsScreen";
import { AppointmentDetailScreen } from "../screens/AppointmentDetailScreen";
import { LabResultsScreen } from "../screens/LabResultsScreen";
import { LabOrderDetailScreen } from "../screens/LabOrderDetailScreen";
import { InvoicesListScreen } from "../screens/InvoicesListScreen";
import { InvoiceDetailScreen } from "../screens/InvoiceDetailScreen";
import { ProfileScreen } from "../screens/ProfileScreen";
import type {
  AppointmentsStackParamList,
  BillingStackParamList,
  LabResultsStackParamList,
} from "./types";

const Tab = createBottomTabNavigator();
const AppointmentsStack = createNativeStackNavigator<AppointmentsStackParamList>();
const LabResultsStack = createNativeStackNavigator<LabResultsStackParamList>();
const BillingStack = createNativeStackNavigator<BillingStackParamList>();

const stackHeaderOptions = {
  headerStyle: { backgroundColor: "#0f2c52" },
  headerTintColor: "#fff",
  headerTitleStyle: { fontWeight: "700" as const },
};

function AppointmentsStackNavigator() {
  return (
    <AppointmentsStack.Navigator screenOptions={stackHeaderOptions}>
      <AppointmentsStack.Screen
        name="AppointmentsList"
        component={AppointmentsScreen}
        options={{ title: "Appointments" }}
      />
      <AppointmentsStack.Screen
        name="AppointmentDetail"
        component={AppointmentDetailScreen}
        options={{ title: "Appointment" }}
      />
    </AppointmentsStack.Navigator>
  );
}

function LabResultsStackNavigator() {
  return (
    <LabResultsStack.Navigator screenOptions={stackHeaderOptions}>
      <LabResultsStack.Screen
        name="LabResultsList"
        component={LabResultsScreen}
        options={{ title: "Lab Results" }}
      />
      <LabResultsStack.Screen
        name="LabOrderDetail"
        component={LabOrderDetailScreen}
        options={{ title: "Lab Order" }}
      />
    </LabResultsStack.Navigator>
  );
}

function BillingStackNavigator() {
  return (
    <BillingStack.Navigator screenOptions={stackHeaderOptions}>
      <BillingStack.Screen
        name="InvoicesList"
        component={InvoicesListScreen}
        options={{ title: "Billing" }}
      />
      <BillingStack.Screen
        name="InvoiceDetail"
        component={InvoiceDetailScreen}
        options={{ title: "Invoice" }}
      />
    </BillingStack.Navigator>
  );
}

const TAB_ICONS: Record<string, string> = {
  Home: "\u{1F3E0}",
  Appointments: "\u{1F4C5}",
  "Lab Results": "\u{1F9EA}",
  Billing: "\u{1F4B3}",
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
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
        tabBarStyle: { height: 62, paddingBottom: 8, paddingTop: 6 },
        tabBarIcon: ({ focused }) => <TabIcon route={route.name} focused={focused} />,
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen
        name="Appointments"
        component={AppointmentsStackNavigator}
        options={{ headerShown: false }}
      />
      <Tab.Screen
        name="Lab Results"
        component={LabResultsStackNavigator}
        options={{ headerShown: false }}
      />
      <Tab.Screen
        name="Billing"
        component={BillingStackNavigator}
        options={{ headerShown: false }}
      />
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
