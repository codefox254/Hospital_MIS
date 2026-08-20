import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { RequireAuth, RequirePermission } from "./components/layout/RequireAuth";
import { queryClient } from "./lib/queryClient";
import { AppointmentsListPage } from "./pages/appointments/AppointmentsListPage";
import { BookAppointmentPage } from "./pages/appointments/BookAppointmentPage";
import { LoginPage } from "./pages/auth/LoginPage";
import { DashboardPage } from "./pages/dashboard/DashboardPage";
import { CreateLabOrderPage } from "./pages/laboratory/CreateLabOrderPage";
import { LabOrderDetailPage } from "./pages/laboratory/LabOrderDetailPage";
import { LabOrdersListPage } from "./pages/laboratory/LabOrdersListPage";
import { ConsultationWorkspace } from "./pages/opd/ConsultationWorkspace";
import { StartVisitPage } from "./pages/opd/StartVisitPage";
import { VisitsListPage } from "./pages/opd/VisitsListPage";
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

            <Route
              path="/opd"
              element={
                <RequirePermission code="opd.visit.view">
                  <VisitsListPage />
                </RequirePermission>
              }
            />
            <Route
              path="/opd/new"
              element={
                <RequirePermission code="opd.visit.create">
                  <StartVisitPage />
                </RequirePermission>
              }
            />
            <Route
              path="/opd/:id"
              element={
                <RequirePermission code="opd.visit.view">
                  <ConsultationWorkspace />
                </RequirePermission>
              }
            />

            <Route
              path="/laboratory"
              element={
                <RequirePermission code="laboratory.lab_order.view">
                  <LabOrdersListPage />
                </RequirePermission>
              }
            />
            <Route
              path="/laboratory/new"
              element={
                <RequirePermission code="laboratory.lab_order.create">
                  <CreateLabOrderPage />
                </RequirePermission>
              }
            />
            <Route
              path="/laboratory/:id"
              element={
                <RequirePermission code="laboratory.lab_order.view">
                  <LabOrderDetailPage />
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
