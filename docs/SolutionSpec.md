# FDO Hospital MIS — Solution Specification & Architecture Document

> Converted from the source `.docx` for in-repo, greppable reference. Table structure was
> flattened during conversion (one cell/paragraph per line) — treat this as a faithful text
> extraction, not a pixel-exact re-render of the original tables.

Solution Specification & Architecture Document  
Node & Connection Architecture · System Flows · UI/UX Journeys per Channel  
Prepared for FDO Technologies  
Draft — Version 0.1  
August 2026  
Field  
Detail  
Document Status  
Draft — for internal review  
Version  
0.1  
Owner  
Solutions Architecture / Product Design  
Channels Covered  
Web Console (React) · Mobile App — FDO Health (React Native) · Backend Platform (Django)  
Companion Documents  
FDO Hospital MIS — Business Requirements Document; Technical Requirements Document  
Table of Contents  
## 1. Introduction & Scope
This Solution Specification & Architecture Document translates the Business Requirements Document (BRD) and Technical Requirements Document (TRD) into a concrete system: the nodes that make it up, how those nodes connect, how data moves through the system for each major workflow, and — since a system this clinically dense lives or dies on whether the right person can act fast — what the actual screen-by-screen journey looks like for each channel.  
Three channels are in scope, per the confirmed stack:  
Web Console (React) — the staff-facing application: administrators, receptionists, doctors, nurses, lab/radiology staff, pharmacists, billing/finance staff. This is the system shown in the reference UI: sidebar navigation, dashboard, patient profile, appointments, ward map, OPD consultation, lab results, invoicing, and dispensing.  
Mobile App — FDO Health (React Native) — the patient-facing application: booking, appointments, lab results, and profile, matching the three reference mobile screens.  
Backend Platform (Django) — the single API and data platform both channels consume, plus the integrations (M-Pesa, SMS/WhatsApp, insurance) that connect the hospital to the outside world.  
## 2. Solution Overview
At the highest level, the solution is a client-server platform with two first-party clients (web and mobile) talking to one Django backend over a versioned REST API, with a WebSocket channel layered in for the real-time elements the reference UI depends on — the live appointment queue, the live bed-status grid, and critical lab-value alerts. The backend in turn talks outward to payment, messaging, and insurance providers.  
Web Console (React)  
Mobile App — FDO Health (React Native)  
↓  HTTPS (REST) + WSS (real-time)  
Load Balancer / API Gateway (Nginx)  
↓  
Django REST API  
Django Channels (WebSocket)  
↓  
Celery Workers  
PostgreSQL  
Redis  
Object Storage  
↓  
M-Pesa Daraja  
SMS / WhatsApp / Email  
Insurance APIs  
PACS (future)  
This diagram is intentionally simplified for orientation; Section 3 breaks every one of these boxes into a full node inventory with responsibilities and connections, and Section 5 walks through how data actually moves for each of the platform's core workflows.  
## 3. High-Level Architecture — Node Inventory & Connections
### 3.1 Node Inventory
Node  
Type  
Responsibility  
Web Client (React SPA)  
First-party client  
Staff-facing console — dashboard, patient records, OPD, ward, lab, billing, admin. Renders conditionally by role/permission.  
Mobile Client (React Native — FDO Health)  
First-party client  
Patient-facing app — booking, appointments, results, profile. Future Clinician/Staff apps share this codebase.  
CDN  
Delivery  
Serves the built web app's static assets and mobile OTA update bundles close to the user.  
Load Balancer / Reverse Proxy (Nginx)  
Edge  
TLS termination, routes traffic to Django app servers, absorbs basic rate limiting.  
Django REST API  
Application  
The modular-monolith backend (see TRD Section 4) — all business logic and data access.  
Auth / RBAC Engine  
Application (within Django)  
JWT issuance/validation and the module.resource.action permission engine (BRD Section 8).  
Django Channels (WebSocket layer)  
Application  
Real-time event distribution for the live queue, bed map, and critical alerts.  
Celery Workers  
Application  
Async task execution — notifications, payment callbacks, scheduled jobs, report generation.  
Celery Beat  
Application  
Cron-style scheduler for recurring jobs (reminders, expiry checks, reconciliation).  
Redis  
Data / messaging  
Celery broker & result backend, Channels layer, application cache.  
PostgreSQL — Primary  
Data  
System of record for every module; all writes land here.  
PostgreSQL — Read Replica  
Data  
Serves reporting/analytics reads so they never compete with transactional load.  
Object Storage (S3-compatible)  
Data  
Patient photos, documents, lab/imaging attachments, generated PDFs (invoices, reports).  
Audit Log Store  
Data  
Independent, append-only record of every clinical/financial write (BRD Section 7.3).  
Notification Dispatch  
Integration  
Abstraction layer routing to SMS/WhatsApp, email, and push providers.  
M-Pesa Daraja Gateway  
External integration  
STK Push collection and payment-confirmation callback (TRD Section 9).  
Insurance Partner APIs  
External integration  
Per-insurer adapters for eligibility, pre-authorization, and claims.  
PACS / DICOM (future)  
External integration  
Radiology image store — Phase 2+; manual upload is the interim path.  
Analytics / Reporting Layer  
Application  
Read-only aggregation over the replica, powering BRD Section 6.18 dashboards.  
CI/CD Pipeline  
Platform  
Builds, tests, and deploys both frontends and the backend across environments (TRD Section 11).  
Monitoring & Alerting  
Platform  
Observability across every node above — latency, error rate, uptime (TRD Section 11.4).  
### 3.2 Connections
From  
To  
Protocol  
Data Exchanged  
Web Client  
CDN  
HTTPS  
Static assets (JS/CSS bundle)  
Web Client  
Load Balancer  
HTTPS (REST)  
API requests, JWT bearer token  
Web Client  
Django Channels  
WSS  
Live queue, bed-status, and alert events  
Mobile Client  
Load Balancer  
HTTPS (REST)  
API requests, JWT bearer token  
Mobile Client  
FCM (push)  
HTTPS  
Push token registration; receives appointment/result/refill notifications  
Load Balancer  
Django REST API  
HTTP (internal)  
Routed, TLS-terminated requests  
Django REST API  
PostgreSQL Primary  
SQL (TCP)  
All transactional reads/writes  
Analytics / Reporting Layer  
PostgreSQL Read Replica  
SQL (TCP)  
Aggregate/report queries  
Django REST API  
Redis  
Redis protocol  
Cache get/set, session & permission-set lookups  
Django REST API  
Celery (via Redis broker)  
Redis protocol  
Async task enqueue (notifications, callbacks, jobs)  
Celery Workers  
PostgreSQL Primary  
SQL (TCP)  
Task-driven writes (e.g. reconciliation, reminders)  
Celery Workers  
Notification Dispatch  
Internal call  
Message payload (SMS/WhatsApp/email/push)  
Notification Dispatch  
SMS / WhatsApp / Email Providers  
HTTPS / SMTP  
Outbound message content  
Django REST API  
M-Pesa Daraja Gateway  
HTTPS (REST)  
STK Push collection request  
M-Pesa Daraja Gateway  
Django REST API (webhook)  
HTTPS (callback)  
Payment confirmation, processed via Celery  
Django REST API  
Insurance Partner APIs  
HTTPS (REST/SOAP, per adapter)  
Eligibility check, pre-auth, claim submission  
Django REST API  
Object Storage  
HTTPS (S3 API)  
File upload/download (documents, images, PDFs)  
Django REST API  
Audit Log Store  
Internal write  
Field-level diff, actor, timestamp per clinical/financial write  
Django Channels  
Redis  
Redis pub/sub  
Real-time event fan-out to connected clients  
CI/CD Pipeline  
Container Registry → Orchestration Platform  
Registry push / deploy API  
Versioned, immutable release artifacts  
Monitoring & Alerting  
All application nodes  
Metrics/log scrape or push  
Latency, error rate, uptime, resource utilization  
## 4. Component Architecture Detail
### 4.1 Backend — Django Modular Monolith
The full breakdown of Django apps, their responsibilities, and the API/data/security standards they follow is defined in the Technical Requirements Document, Sections 4 and 7–8, and is not repeated here. The key architectural fact this document builds on: every module is independently addressable via /api/v1/<module>/ and no module reaches into another module's database tables directly — cross-module data flows as the events listed in Section 3.2 and the BRD's Cross-Module Integration Map (BRD Section 9).  
### 4.2 Web Console — React Component Layers
Layer  
Contents  
Shell  
Sidebar navigation, top bar (search, notifications, user menu), role-aware route guard — visible in every reference screen as the persistent left rail and header  
Design system  
Shared components: KPI card, donut/line chart wrappers, status badge (color-coded per BRD status vocabulary — Scheduled/Checked-In/Completed etc.), data table, tabbed detail panel, split-panel workspace  
Domain screens  
One screen group per Django app / BRD module — Dashboard, Patients, Appointments, OPD, Inpatients, Laboratory, Radiology, Pharmacy, Billing, Insurance, Inventory, HR & Payroll, Reports, Settings — matching the sidebar in the reference UI exactly  
Real-time layer  
WebSocket-subscribed components: the appointment queue list, the ward bed grid, and critical-alert banners  
Data layer  
React Query hooks per module, wrapping the versioned REST API defined in the TRD  
### 4.3 Mobile App — React Native Component Layers
Layer  
Contents  
Navigation shell  
Bottom tab navigator — Home, Appointments, Results, Profile — matching the reference mobile screens exactly  
Design system  
Shared components mirrored conceptually from the web design system: appointment card, result-status badge, action tile grid  
Domain screens  
Home (dashboard/greeting), Book Appointment, Appointment List & Detail, Lab Results List & Detail, Profile & Billing  
Offline/local layer  
Cached last-synced data, queued offline actions, encrypted token storage (TRD Section 6.2)  
Data layer  
React Query hooks against the same versioned REST API as the web console  
## 5. System Flow Diagrams
Each flow below traces a single BRD user journey through the actual nodes from Section 3 — this is the level of detail engineering needs to implement the request/response and async-task chain correctly, and it is where the BRD's edge cases (Section 6 of the BRD) usually turn into a specific validation or a specific async retry.  
### 5.1 Patient Registration & MRN Generation
#  
Node / Actor  
Action  
Target Node  
Protocol / Notes  
1  
Receptionist (Web Client)  
Searches for an existing patient by name/phone/ID  
Django REST API → PostgreSQL  
GET /api/v1/patients/?search= — de-duplication check per BRD edge case  
2  
Receptionist (Web Client)  
Submits new patient demographics, consent, and photo  
Django REST API  
POST /api/v1/patients/ — multipart for photo, routed to Object Storage  
3  
Django REST API  
Generates a unique MRN and persists the record  
PostgreSQL Primary  
Transactional write; MRN generation is server-side, never client-supplied  
4  
Django REST API  
Writes the creation event  
Audit Log Store  
Actor, timestamp, full field snapshot  
5  
Django REST API  
Returns the created patient record  
Web Client  
200/201 response; UI routes to Appointments or OPD per BRD journey  
### 5.2 Appointment Booking (Web & Mobile) → Queue
#  
Node / Actor  
Action  
Target Node  
Protocol / Notes  
1  
Patient (Mobile) or Receptionist (Web)  
Requests a slot for a department/doctor/date  
Django REST API  
GET /api/v1/appointments/availability/  
2  
Django REST API  
Locks and confirms the slot  
PostgreSQL Primary  
Row-level lock prevents the double-booking edge case from the BRD  
3  
Django REST API  
Enqueues a confirmation + reminder task  
Celery (via Redis)  
Async — never blocks the booking response  
4  
Celery Worker  
Dispatches confirmation now, reminder later (Celery Beat)  
Notification Dispatch → SMS/WhatsApp/Push  
Reminder job scheduled ~24h pre-appointment per BRD story  
5  
Patient checks in (Web reception or Mobile)  
Marks arrival  
Django REST API  
PATCH /api/v1/appointments/{id}/check-in/  
6  
Django REST API  
Publishes a queue-updated event  
Django Channels → Redis pub/sub  
Fanned out to every subscribed Web Client (reception queue view, nurse view)  
7  
Web Client (reception, nursing, doctor)  
Receives live queue update  
WebSocket push  
Queue list and position update without a manual refresh  
### 5.3 OPD Consultation → Orders Dispatch
#  
Node / Actor  
Action  
Target Node  
Protocol / Notes  
1  
Nurse (Web Client)  
Records vitals against the active visit  
Django REST API  
POST /api/v1/opd/visits/{id}/vitals/  
2  
Doctor (Web Client)  
Opens the consultation workspace (Chief Complaint / History / Examination / Diagnosis tabs, per reference UI)  
Django REST API  
GET /api/v1/patients/{id}/timeline/ + GET /api/v1/opd/visits/{id}/  
3  
Doctor (Web Client)  
Saves diagnosis and treatment plan (prescription, lab/imaging orders)  
Django REST API  
PATCH /api/v1/opd/visits/{id}/; auto-saved as draft per BRD's interrupted-consultation edge case  
4  
Django REST API  
Creates linked orders  
Laboratory / Radiology / Pharmacy apps (internal, same transaction where possible)  
Each order created with status = pending, owning module notified  
5  
Django REST API  
Finalizes and locks the consultation note  
PostgreSQL Primary  
Further changes require an addendum, not an edit (BRD edge case)  
6  
Django REST API  
Generates the billable line items  
Billing app (internal)  
Consultation + any billable order items, per the "every service is billable" principle  
### 5.4 Lab Order → Result → Verification → Notification
#  
Node / Actor  
Action  
Target Node  
Protocol / Notes  
1  
Django REST API  
Receives the lab order from OPD (Flow 5.3, step 4)  
Laboratory app  
Order created, status = pending, billing/insurance check triggered  
2  
Lab Technician (Web Client)  
Logs sample collection, prints barcode  
Django REST API  
POST /api/v1/laboratory/samples/  
3  
Lab Technician (Web Client)  
Enters raw results against the CBC/panel screen (per reference UI)  
Django REST API  
PATCH /api/v1/laboratory/results/{id}/ — status = entered, not yet visible to the doctor  
4  
Lab Scientist (Web Client)  
Reviews and verifies (or amends) the result  
Django REST API  
PATCH .../verify/ — status = verified; technician cannot self-verify (BRD permission rule)  
5  
Django REST API  
If any value is flagged critical  
Celery (priority queue) → Notification Dispatch  
Bypasses standard notification queue — target latency < 60s per TRD Section 3.1  
6  
Django REST API  
Releases the verified result  
Web Client (Doctor) + Mobile Client (Patient, per release policy)  
Doctor sees it in the patient timeline; patient sees it in the FDO Health Lab Results screen  
### 5.5 Inpatient Admission → Bed Allocation → Discharge
#  
Node / Actor  
Action  
Target Node  
Protocol / Notes  
1  
Doctor (Web Client)  
Requests admission with diagnosis and initial orders  
Django REST API  
POST /api/v1/inpatient/admissions/  
2  
Ward Clerk (Web Client, Ward map per reference UI)  
Allocates a bed from the live bed-status grid  
Django REST API  
PATCH /api/v1/inpatient/beds/{id}/ — status Available → Occupied  
3  
Django REST API  
Publishes bed-status change  
Django Channels → Redis pub/sub  
Every connected Ward Map view updates live  
4  
Nurse (Web Client)  
Executes daily orders (vitals, MAR, notes)  
Django REST API  
Nursing app, linked to the admission record  
5  
Doctor (Web Client)  
Initiates discharge; system runs the discharge checklist (pending labs/bills)  
Django REST API → Billing app  
GET /api/v1/billing/invoices/?visit= — blocks discharge completion until reviewed, per BRD edge case  
6  
Ward Clerk (Web Client)  
Confirms discharge  
Django REST API  
Bed status Occupied → Cleaning → (auto) Available  
### 5.6 Pharmacy Dispensing (Outpatient)
#  
Node / Actor  
Action  
Target Node  
Protocol / Notes  
1  
Django REST API  
Prescription created in OPD (Flow 5.3)  
Pharmacy app  
Order created, status = pending, routed to the pharmacy queue  
2  
Pharmacist (Web Client, Dispense screen per reference UI)  
Checks stock and interaction/allergy screening  
Django REST API  
GET /api/v1/pharmacy/stock/ cross-referenced with patient allergy data  
3  
Pharmacist (Web Client)  
Confirms dispensing  
Django REST API  
POST /api/v1/pharmacy/dispense/ — decrements stock transactionally  
4  
Django REST API  
Generates the billable line item  
Billing app (internal)  
Per-item pricing from the pharmacy catalogue  
5  
Django REST API  
Checks resulting stock level against reorder threshold  
Inventory & Procurement app  
If breached, a stock-request event is raised automatically  
### 5.7 Billing & M-Pesa Payment
#  
Node / Actor  
Action  
Target Node  
Protocol / Notes  
1  
Cashier (Web Client, Invoice screen per reference UI)  
Selects M-Pesa as the payment method and initiates collection  
Django REST API  
POST /api/v1/billing/payments/mpesa/stk-push/ with an Idempotency-Key header  
2  
Django REST API  
Initiates STK Push  
M-Pesa Daraja Gateway  
HTTPS REST call; invoice held status = pending confirmation, per BRD edge case  
3  
Patient's phone  
Approves the payment prompt  
M-Pesa Daraja Gateway  
Handled entirely within Safaricom's infrastructure  
4  
M-Pesa Daraja Gateway  
Sends the payment result  
Django REST API (webhook endpoint)  
HTTPS callback, processed asynchronously via Celery to avoid blocking on gateway latency  
5  
Celery Worker  
Matches the callback to the originating invoice and marks it settled  
PostgreSQL Primary  
Idempotency key prevents double-processing on a retried callback  
6  
Django REST API  
Issues the receipt  
Web Client (Cashier) + Mobile Client (Patient, via portal/billing history)  
Invoice status flips to Paid across every channel  
### 5.8 Mobile App — Login & Data Sync (FDO Health)
#  
Node / Actor  
Action  
Target Node  
Protocol / Notes  
1  
Patient (Mobile Client)  
Authenticates (credentials or biometric re-auth)  
Django REST API  
POST /api/v1/auth/token/ — JWT access + refresh pair issued  
2  
Mobile Client  
Fetches Home-screen data: upcoming appointment, quick actions  
Django REST API  
GET /api/v1/appointments/upcoming/ + patient profile summary  
3  
Mobile Client  
Registers device for push notifications  
Django REST API → FCM  
Token stored against the patient's account for future reminders/alerts  
4  
Mobile Client (offline)  
Serves last-synced appointments/results from local cache  
Local encrypted storage  
Clearly labeled "last synced at [time]" per TRD Section 6.2  
5  
Mobile Client (reconnect)  
Submits any queued offline actions (e.g. a booking attempt)  
Django REST API  
Uses the same Idempotency-Key pattern as Flow 5.7 to avoid duplicate bookings  
## 6. Deployment Architecture
### 6.1 Environments
Development, Staging, and Production run as isolated deployments of the same containerized architecture (TRD Section 11.1), differing in scale and data — never in topology, so a bug caught in Staging is trustworthy evidence about Production behavior.  
### 6.2 Production Topology
Web and mobile clients reach the platform through a CDN (static assets) and a load-balanced set of stateless Django app-server containers — no session state lives on an individual app server, so any instance can be recycled or scaled without disrupting active users.  
Celery workers run as a separately scaled pool from the Django API containers, since notification/payment/report workloads have a different scaling profile than request/response API traffic.  
PostgreSQL runs as a managed primary with at least one read replica from Phase 1, per TRD Section 8.1 — this is the one piece of infrastructure most expensive to retrofit later, so it is provisioned correctly from the start even while load is low.  
Redis, object storage, and the container registry are managed services rather than self-hosted, to keep operational burden focused on the application itself rather than infrastructure plumbing, given the team's likely size in Phase 1.  
### 6.3 Multi-Facility Scaling (Phase 3)
Because every core model already carries a facility_id (TRD Section 8.1), horizontal growth to a hospital group is primarily a capacity question, not a redesign — additional facilities are new rows, not new schemas or new deployments. Section 6 of the TRD's NFRs revisit the 99.9% uptime target at the point multiple facilities depend on the platform simultaneously.  
## 7. UI/UX Journeys per Channel
The journeys below are written directly against the reference UI supplied for this platform — the same navigation structure, screen names, panels, and status vocabulary are used here so design and engineering are building the same product the mockups describe, not a reinterpretation of it.  
### 7.1 Design System Foundations
Before the individual journeys, a few visual/interaction conventions are worth locking in as system-wide rules, because they recur across almost every screen in the reference UI:  
Persistent left sidebar (web) — navy background, white active-state highlight, one entry per top-level module (Dashboard, Appointments, Patients, OPD, Inpatients, Emergency, Laboratory, Radiology, Pharmacy, Billing, Insurance, Inventory, HR & Payroll, Reports, Settings). This is the primary navigation for every staff role; visible entries are filtered by the logged-in user's permissions, not hidden by CSS.  
Top bar (web) — global search ("Search patients, appointments, invoices…"), notification bell, mail icon, and a user badge showing name + role (e.g. "Dr. John Mwangi / Administrator"). Present on every screen, consistent placement.  
KPI cards — a row of compact metric cards (value, label, trend delta vs. yesterday) used on the Dashboard and repeatable on any module landing screen (e.g. Appointments' status-count summary).  
Status badges — a single, consistent color vocabulary for state across the whole product: e.g. green for Completed/Verified/Paid/Available, blue for Scheduled/In Progress, amber for Reserved/Pending, red for Cancelled/Critical/Overdue, grey for No Show/Cleaning/Inactive. A status means the same color everywhere it appears.  
Split-panel workspace — the pattern used by OPD Consultation, Laboratory Results, and Dispense Prescription: a left rail of sub-sections/tests, a right-hand detail/entry panel. This is the standard pattern for any "work through a structured record" screen, not bespoke per module.  
Tabbed record view — the pattern used by Patient Profile (Overview, Visits, Admissions, Lab Results, Imaging, Prescriptions, Bills, Documents): one entity, many facets, one tab bar. Reused for any other "single record, many related facets" screen (e.g. a staff profile, a supplier profile).  
Grid-of-cells pattern — the ward bed map's color-coded grid (Occupied / Available / Reserved / Cleaning / Maintenance / Isolation) is the template for any other visual capacity view (e.g. a future theatre schedule grid).  
Mobile bottom tab bar — four destinations for the patient app: Home, Appointments, Results, Profile — deliberately shallow navigation, since patients open this app briefly and infrequently rather than working within it for hours.  
### 7.2 Web Console Journeys, by Persona
### 7.2.1 Hospital Administrator — Daily Oversight
Logs in and lands on the Dashboard: KPI cards for Today's Patients, OPD Visits, Inpatients, Bed Occupancy, and Revenue Today, each with a trend delta against yesterday.  
Scans the Revenue Overview line chart (This Month) and the Patients by Department donut for anything that looks off relative to a normal day.  
Reviews the Department Performance table (patients, revenue, expenses, profit, trend sparkline per department) to spot an underperforming or overloaded department.  
Checks the Bed Occupancy donut (Occupied / Available / Reserved / Maintenance) for capacity risk.  
Scrolls the Recent Activities feed (new registrations, lab verifications, payments, admissions, dispensing) as a live pulse of the hospital, with a "View all" escape hatch into full activity/audit history.  
Navigates via the sidebar into a specific module (e.g. Billing, HR & Payroll, Reports) when a metric warrants a closer look.  
### 7.2.2 Receptionist — Registration, Appointments & Queue
Uses the global search bar to check whether an arriving patient already exists before registering them.  
Opens the Appointments module: sees the mini calendar (current month, selected day highlighted), the day's appointment list (time, patient, type, doctor, status), and the status-count summary (Scheduled / Checked In / In Consultation / Completed / No Show / Cancelled).  
Creates a walk-in or new appointment via "+ New Appointment," filtering by department/doctor/status as needed to find an open slot.  
Checks a patient in on arrival — their status chip flips from Scheduled to Checked In, and the change appears live in every other staff member's queue view via the real-time layer (Flow 5.2).  
Opens Patient Profile when needed to confirm or update demographics, insurance, or emergency contact, using the tabbed record view.  
### 7.2.3 Doctor — OPD Consultation
From the queue or appointment list, opens the patient's active visit — the OPD Consultation split-panel workspace loads with an "Active Visit" badge and timestamp.  
Works down the left-hand section list — Vitals (pre-filled by the nurse), Chief Complaint, History, Examination, Diagnosis, Investigations, Prescription, Procedures, Notes, Documents — each opening its structured entry form in the right-hand panel.  
Reviews vitals already captured (BP, Pulse, Temp, Resp, SpO2, Weight, Height) and documents History of Present Illness and Examination findings.  
Records Primary and Secondary Diagnosis (ICD-coded, as shown in the reference UI's "I10 — Essential (primary) hypertension" style), then adds Investigations (e.g. FBS, Lipid Profile, ECG) and Prescription items directly from the same screen.  
Uses "Save as Draft" at any point — critical for the BRD's interrupted-consultation edge case — and "Complete Consultation" to finalize, lock, and dispatch every order to Laboratory, Radiology, and Pharmacy simultaneously (Flow 5.3).  
### 7.2.4 Nurse / Ward Clerk — Inpatient Ward
Opens Inpatient → selects a ward (e.g. "Ward A") from the ward selector; sees Total Beds, Occupied/Available/Reserved/Maintenance counts, and the full color-coded bed grid (A01–A40).  
Identifies an available bed visually (color-coded, per Section 7.1's grid pattern) and allocates it via "+ New Admission," or moves a patient via "⇄ Transfer Patient."  
Clicks into an occupied bed to see the assigned patient and primary diagnosis at a glance (as shown for beds A02 and A04 in the reference UI), without leaving the ward view.  
Documents vitals, nursing notes, and medication administration against the patient's admission record throughout the shift (Nursing module, per BRD Section 6.5).  
At handover, compiles the shift summary; the incoming nurse acknowledges it before assuming care, per the BRD's Nursing journey.  
### 7.2.5 Lab Technician / Lab Scientist — Laboratory
Opens Laboratory Results for the patient (via the order queue or direct search); sees sample-collection metadata (date collected) and a left-hand list of ordered test panels (CBC active, FBS, Lipid Profile, Liver Function, U&E, Urinalysis).  
Lab Technician selects a panel (e.g. Complete Blood Count) and enters raw results against the structured table (Test, Result, Unit, Reference Range, Status), which auto-flags any out-of-range value.  
Lab Scientist reviews the entered results — visible as "Result Entered by [Technician], [timestamp]" — and verifies, which stamps "Verified by [Scientist], [timestamp]" and flips the status badge to Verified.  
Prints or releases the report via "Print Report"; a verified, released result becomes visible to the ordering doctor immediately and to the patient in the FDO Health Lab Results screen per release policy.  
### 7.2.6 Billing Officer / Cashier — Invoicing & Dispensing
Opens the Invoice screen for a visit (e.g. INV-2024-001234): sees the itemized Services table (consultation, tests, medications with quantity/unit price/amount), Subtotal, Discount, Tax, Total, Paid, and Balance.  
Collects payment (cash, card, or M-Pesa); on M-Pesa, the invoice moves to "pending confirmation" until the Daraja callback lands (Flow 5.7), then flips to Paid with the Balance shown as 0.00.  
Prints or downloads the receipt; the same record is visible to the patient in FDO Health's billing history.  
For pharmacy items specifically, a Pharmacist works the parallel Dispense Prescription screen — medication table with Qty Prescribed vs. Qty Dispensed, Unit Price, Total, and live Stock Information (in-stock count, batch, expiry) per item — confirming via "Confirm Dispense," which generates the billable line item Billing then displays.  
### 7.3 Mobile App Journeys — FDO Health (React Native)
### 7.3.1 Onboarding & Home
Patient installs the app, registers or logs in (credentials, with biometric re-auth available thereafter per TRD Section 6.1).  
Lands on Home: a greeting ("Hello, John — How can we help you today?"), a four-tile action grid (Book Appointment, My Appointments, Lab Results, My Profile), and an Upcoming Appointment card showing doctor, specialty, date/time, and status.  
A prominent "Book New Appointment" button is always available from Home, not buried in a sub-menu, since booking is the single most common reason a patient opens the app.  
### 7.3.2 Book & Manage Appointments
From Home or the Appointments tab, taps Book Appointment; selects department/doctor and an available slot (same availability the Receptionist sees in the web console, per the shared API — Flow 5.2).  
Confirms; receives an immediate in-app confirmation and, per Flow 5.2, an SMS/WhatsApp confirmation plus a scheduled reminder.  
The Appointments tab shows Upcoming and History sub-tabs; each appointment is a card (doctor, specialty, date/time, status badge — Scheduled, Checked In, Completed) matching the reference UI's three example cards (Dr. John Mwangi, Dr. Grace Njeri, Dr. Mercy Wairimu).  
Can reschedule or cancel an upcoming appointment directly from its card, subject to the booking-rule constraints defined in the BRD (Section 6.2).  
### 7.3.3 View Lab Results
Opens the Results tab: All / Pending / Completed sub-tabs, each result shown as a card with test name, date, and a status badge (Normal, or an out-of-range flag).  
Taps into a result (e.g. Fasting Blood Sugar — 5.4 mmol/L, Normal) to see the full breakdown, matching the detail available to the doctor in the web console's Laboratory Results screen, but presented in plain language rather than the clinical entry table.  
Results only appear here once verified and released per the LIS workflow (Flow 5.4) — never in an entered-but-unverified state, protecting the patient from an unchecked value.  
### 7.3.4 Profile & Billing
The Profile tab surfaces demographics, insurance details, and a link into billing history — invoices and payment status mirrored from the web console's Invoice screen.  
Patients can view and download past invoices/receipts, and — per the BRD's Phase 4 scope — eventually pay an outstanding balance directly from this screen via the same M-Pesa integration used at the cashier desk.  
### 7.4 Screen Inventory
Screen  
Channel  
Primary Actor(s)  
Key Actions  
Related BRD Module  
Dashboard  
Web  
Administrator, Medical Director, CEO  
Monitor KPIs, revenue, occupancy, department performance  
BRD §6.18 Admin & Analytics  
Patient Profile  
Web  
Doctor, Nurse, Receptionist, Registration Officer  
View/edit patient record across Overview, Visits, Admissions, Labs, Imaging, Prescriptions, Bills, Documents  
BRD §6.1 Patient Management  
Appointments  
Web  
Receptionist, Doctor, Patient (via mobile)  
Book, check in, manage the daily schedule and queue  
BRD §6.2 Appointments & Queue  
Inpatient — Ward Map  
Web  
Ward Clerk, Nurse, Doctor  
Allocate beds, admit, transfer, monitor occupancy  
BRD §6.4 Inpatient / Ward  
OPD Consultation  
Web  
Doctor, Clinical Officer, Nurse  
Document a visit and dispatch orders  
BRD §6.3 OPD / Clinical  
Laboratory Results  
Web  
Lab Technician, Lab Scientist, Doctor  
Enter and verify results per test panel  
BRD §6.6 Laboratory (LIS)  
Invoice  
Web  
Cashier, Billing Officer, Patient (via mobile)  
Review, collect payment, issue receipt  
BRD §6.9 Billing & Revenue  
Dispense Prescription  
Web  
Pharmacist, Pharmacy Technician  
Confirm dispensing against stock  
BRD §6.8 Pharmacy  
Home  
Mobile  
Patient  
Quick actions and upcoming appointment at a glance  
BRD §7.1 Patient Portal & Mobile Apps  
Appointments (mobile)  
Mobile  
Patient  
Book, view, and manage appointments  
BRD §6.2 Appointments & Queue  
Lab Results (mobile)  
Mobile  
Patient  
View released results  
BRD §6.6 Laboratory (LIS)  
Profile & Billing (mobile)  
Mobile  
Patient  
View demographics, insurance, invoices/receipts  
BRD §6.1 / §6.9  
## 8. Cross-Cutting UX Principles
Consistency over novelty — a status color, an icon, or a layout pattern means the same thing everywhere it's used (Section 7.1). This is what lets a Nurse who has never opened the Billing module still recognize a status badge at a glance.  
Loading, empty, and error states are designed, not defaulted — every list/table in Section 7.4's screen inventory needs an explicit empty state (e.g. "No appointments scheduled today") and error state (e.g. a failed save in OPD Consultation must never silently lose the doctor's draft, per the BRD edge case), not a blank screen or a generic crash.  
Real-time where it's clinically load-bearing, polling elsewhere — the queue, bed map, and critical alerts use the WebSocket layer (Section 5.2, 5.4, 5.5); a report or a historical list does not need the same infrastructure and should use a normal request/response fetch.  
Role-aware rendering, not role-aware routing alone — the sidebar, the Dashboard's KPI set, and screen actions (e.g. "Approve Refund") are filtered by the BRD's permission matrices at render time, not just gated by whether a route is reachable.  
Mobile is a companion, not a shrink of the web console — the patient app's four-tab structure is deliberately shallower than the staff console's full module list, because the patient's needs (Section 7.3) are a small, frequent subset of the platform's total surface area.  
