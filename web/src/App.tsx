import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { RequireAuth, RequirePermission } from "./components/layout/RequireAuth";
import { queryClient } from "./lib/queryClient";
import { AppointmentsListPage } from "./pages/appointments/AppointmentsListPage";
import { BookAppointmentPage } from "./pages/appointments/BookAppointmentPage";
import { LoginPage } from "./pages/auth/LoginPage";
import { DashboardPage } from "./pages/dashboard/DashboardPage";
import { PatientDetailPage } from "./pages/patients/PatientDetailPage";
import { PatientsListPage } from "./pages/patients/PatientsListPage";
import { RegisterPatientPage } from "./pages/patients/RegisterPatientPage";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            element={
              <RequireAuth>
                <AppLayout />
              </RequireAuth>
            }
          >
            <Route path="/" element={<DashboardPage />} />

            <Route
              path="/patients"
              element={
                <RequirePermission code="patients.patient.view">
                  <PatientsListPage />
                </RequirePermission>
              }
            />
            <Route
              path="/patients/new"
              element={
                <RequirePermission code="patients.patient.create">
                  <RegisterPatientPage />
                </RequirePermission>
              }
            />
            <Route
              path="/patients/:id"
              element={
                <RequirePermission code="patients.patient.view">
                  <PatientDetailPage />
                </RequirePermission>
              }
            />

            <Route
              path="/appointments"
              element={
                <RequirePermission code="appointments.appointment.view">
                  <AppointmentsListPage />
                </RequirePermission>
              }
            />
            <Route
              path="/appointments/new"
              element={
                <RequirePermission code="appointments.appointment.create">
                  <BookAppointmentPage />
                </RequirePermission>
              }
            />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
