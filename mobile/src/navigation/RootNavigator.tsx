import { useCallback, useState } from "react";
import {
  NavigationContainer,
  useNavigationContainerRef,
  type NavigationState,
} from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { StyleSheet, Text, TouchableOpacity } from "react-native";

import { useAuthStore } from "../lib/auth-store";
import { useCurrentUser } from "../lib/useCurrentUser";
import { SideDrawer } from "../components/SideDrawer";
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

function HamburgerButton({ onPress }: { onPress: () => void }) {
  return (
    <TouchableOpacity onPress={onPress} hitSlop={12} style={navStyles.hamburgerButton}>
      <Text style={navStyles.hamburgerIcon}>{"☰"}</Text>
    </TouchableOpacity>
  );
}

function AppointmentsStackNavigator({ onOpenDrawer }: { onOpenDrawer: () => void }) {
  return (
    <AppointmentsStack.Navigator screenOptions={stackHeaderOptions}>
      <AppointmentsStack.Screen
        name="AppointmentsList"
        component={AppointmentsScreen}
        options={{ title: "Appointments", headerLeft: () => <HamburgerButton onPress={onOpenDrawer} /> }}
      />
      <AppointmentsStack.Screen
        name="AppointmentDetail"
        component={AppointmentDetailScreen}
        options={{ title: "Appointment" }}
      />
    </AppointmentsStack.Navigator>
  );
}

function LabResultsStackNavigator({ onOpenDrawer }: { onOpenDrawer: () => void }) {
  return (
    <LabResultsStack.Navigator screenOptions={stackHeaderOptions}>
      <LabResultsStack.Screen
        name="LabResultsList"
        component={LabResultsScreen}
        options={{ title: "Lab Results", headerLeft: () => <HamburgerButton onPress={onOpenDrawer} /> }}
      />
      <LabResultsStack.Screen
        name="LabOrderDetail"
        component={LabOrderDetailScreen}
        options={{ title: "Lab Order" }}
      />
    </LabResultsStack.Navigator>
  );
}

function BillingStackNavigator({ onOpenDrawer }: { onOpenDrawer: () => void }) {
  return (
    <BillingStack.Navigator screenOptions={stackHeaderOptions}>
      <BillingStack.Screen
        name="InvoicesList"
        component={InvoicesListScreen}
        options={{ title: "Billing", headerLeft: () => <HamburgerButton onPress={onOpenDrawer} /> }}
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
    <Text style={focused ? navStyles.tabIconFocused : navStyles.tabIconUnfocused}>
      {TAB_ICONS[route]}
    </Text>
  );
}

const navStyles = StyleSheet.create({
  hamburgerButton: { paddingHorizontal: 12 },
  hamburgerIcon: { fontSize: 22, color: "#fff" },
  tabIconFocused: { fontSize: 22, opacity: 1 },
  tabIconUnfocused: { fontSize: 22, opacity: 0.45 },
});

function MainTabs({ onOpenDrawer }: { onOpenDrawer: () => void }) {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerStyle: { backgroundColor: "#0f2c52" },
        headerTintColor: "#fff",
        headerTitleStyle: { fontWeight: "700" },
        headerLeft: () => <HamburgerButton onPress={onOpenDrawer} />,
        tabBarActiveTintColor: "#0f2c52",
        tabBarInactiveTintColor: "#9ca3af",
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
        tabBarStyle: { height: 62, paddingBottom: 8, paddingTop: 6 },
        tabBarIcon: ({ focused }) => <TabIcon route={route.name} focused={focused} />,
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Appointments" options={{ headerShown: false }}>
        {() => <AppointmentsStackNavigator onOpenDrawer={onOpenDrawer} />}
      </Tab.Screen>
      <Tab.Screen name="Lab Results" options={{ headerShown: false }}>
        {() => <LabResultsStackNavigator onOpenDrawer={onOpenDrawer} />}
      </Tab.Screen>
      <Tab.Screen name="Billing" options={{ headerShown: false }}>
        {() => <BillingStackNavigator onOpenDrawer={onOpenDrawer} />}
      </Tab.Screen>
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

export function RootNavigator() {
  const access = useAuthStore((s) => s.access);
  const logout = useAuthStore((s) => s.logout);
  const { user } = useCurrentUser();
  const navigationRef = useNavigationContainerRef();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("Home");

  const openDrawer = useCallback(() => setDrawerOpen(true), []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);
  const handleNavigate = useCallback(
    (route: string) => {
      navigationRef.navigate(route as never);
      setDrawerOpen(false);
    },
    [navigationRef],
  );
  const handleSignOut = useCallback(() => {
    setDrawerOpen(false);
    logout();
  }, [logout]);
  const handleStateChange = useCallback((state: NavigationState | undefined) => {
    if (!state) return;
    setActiveTab(state.routes[state.index].name);
  }, []);

  return (
    <NavigationContainer ref={navigationRef} onStateChange={handleStateChange}>
      {access ? (
        <>
          <MainTabs onOpenDrawer={openDrawer} />
          <SideDrawer
            visible={drawerOpen}
            activeRoute={activeTab}
            user={user}
            onClose={closeDrawer}
            onNavigate={handleNavigate}
            onSignOut={handleSignOut}
          />
        </>
      ) : (
        <LoginScreen />
      )}
    </NavigationContainer>
  );
}
