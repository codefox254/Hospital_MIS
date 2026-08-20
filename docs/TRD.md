# FDO Hospital MIS — Technical Requirements Document

> Converted from the source `.docx` for in-repo, greppable reference. Table structure was
> flattened during conversion (one cell/paragraph per line) — treat this as a faithful text
> extraction, not a pixel-exact re-render of the original tables.

Technical Requirements Document  
Stack · Non-Functional Requirements · API, Data & Security Standards · DevOps  
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
Solutions Architecture / Engineering Leadership  
Confirmed Stack  
Django + DRF (backend) · React (web) · React Native (mobile)  
Companion Documents  
FDO Hospital MIS — Business Requirements Document; Solution Specification & Architecture Document  
Table of Contents  
## 1. Introduction & Objectives
This Technical Requirements Document (TRD) defines the technology stack, engineering standards, and non-functional requirements for building FDO Hospital MIS. It is the companion to the Business Requirements Document (BRD) — where the BRD defines what the system must do for each actor and module, this document defines how it will be built, on what stack, to what quality bar, and under what constraints.  
Confirmed technology direction:  
Backend: Django + Django REST Framework (Python)  
Web Client (staff/clinical console): React  
Mobile Client (patient-facing FDO Health, and future clinician/staff apps): React Native  
This document assumes PostgreSQL, Redis, and Celery as the supporting data/async stack, and containerized deployment (Docker) as the delivery mechanism — these are the industry-standard pairing for Django at hospital scale and are called out explicitly in Section 3 as assumptions to confirm, not settled decisions made unilaterally.  
### 1.2 Relationship to Other Documents
Document  
Defines  
Business Requirements Document (BRD)  
Modules, actors, roles, permission matrices, user stories, user journeys, edge cases  
Technical Requirements Document (this document)  
Stack, non-functional requirements, API/data/security standards, DevOps  
Solution Specification & Architecture Document  
Node-and-connection architecture, system flows, deployment topology, UI/UX journeys per channel  
## 2. Guiding Engineering Principles
Modular monolith first — Django apps are organized one-per-BRD-module (patients, appointments, opd, inpatient, lab, radiology, pharmacy, billing, insurance, bloodbank, emergency, theatre, ambulance, inventory, hr, finance, admin). This gives the maintainability benefits of clear boundaries without the operational overhead of microservices on day one. Section 4.4 defines how a module can later be extracted into its own service without a rewrite.  
Permission engine, not scattered if-statements — every module reads from the same RBAC engine described in the BRD (Section 8), implemented as Django permission classes bound to the module.resource.action convention. No module should implement bespoke access-control logic.  
Every write is audited — no clinical or financial table is ever hard-deleted or silently overwritten. All writes to clinical/financial models flow through an audit-logging mixin.  
API-first — the Django backend exposes a single versioned REST API consumed identically by the React web console and the React Native mobile app. No logic lives only in a frontend that the other channel depends on.  
Design for intermittent connectivity — target facilities may have unreliable connectivity; the mobile app and, where practical, OPD/Nursing web workflows are designed to tolerate brief disconnection without data loss.  
Facility-scoped from day one — every core model carries a facility (and, where relevant, department) foreign key, even for the first single-facility customer, per the BRD's multi-branch recommendation.  
## 3. Non-Functional Requirements
Non-functional requirements (NFRs) are grouped below with a target, since "the system should be fast/secure/reliable" is not testable. These targets should be revisited once real usage data exists, but give engineering a concrete bar to design against.  
### 3.1 Performance
Requirement  
Target  
API response time (p95, standard read)  
< 400ms  
API response time (p95, complex read — e.g. patient timeline)  
< 1.2s  
OPD consultation screen load  
< 2s on a 3G-equivalent connection  
Dashboard (Section 8 of BRD) load  
< 2.5s for aggregate metrics  
Mobile app cold start  
< 3s  
Concurrent users supported (initial, single mid-size hospital)  
300 concurrent staff sessions  
Lab critical-value notification latency  
< 60s from verification to alert delivery  
### 3.2 Scalability & Availability
Target uptime: 99.5% for Phase 1–2 (single facility), moving to 99.9% once multiple facilities depend on the platform for live clinical operations.  
The backend must scale horizontally — stateless Django app servers behind a load balancer, session/auth state in Redis, not in-process memory.  
Database must support read replicas for reporting/analytics load without impacting transactional (OPD, billing) performance.  
Multi-facility scaling (Phase 3) must not require a schema migration — this is why facility_id is present from Phase 1 (Section 2).  
### 3.3 Security & Compliance
All traffic over TLS 1.2+; no unencrypted endpoint, including internal service-to-service calls in production.  
Encryption at rest for the database and object storage (see BRD Section 7.3).  
Password policy, MFA for privileged roles (Administrator, Finance Manager, IT Administrator, Medical Director), and session timeout enforced at the API layer, not just the frontend.  
Compliance target: Kenya's Data Protection Act, 2019, plus general health-data handling good practice (least-privilege access, audit trails, right-to-access/export for patients). Confirm with legal counsel before go-live whether sector-specific health-data regulation applies beyond the general Data Protection Act.  
OWASP Top 10 mitigations are a release gate, not a nice-to-have — enforced via automated dependency scanning and a pre-launch penetration test.  
### 3.4 Usability & Accessibility
Web console targets desktop-first (clinical/admin staff on workstations) but must remain usable on tablets for ward-side nursing use.  
Mobile app targets Android first, given device distribution in the target market, with iOS as a fast-follow — confirm this assumption with product before mobile work starts.  
WCAG 2.1 AA as a target for the web console's color contrast and keyboard navigation, given clinical staff use this for extended shifts.  
### 3.5 Maintainability
Minimum automated test coverage: 80% for backend business logic (models, serializers, permission classes), 60% for frontend component logic.  
Every Django app ships with its own OpenAPI schema section, generated from DRF serializers — not maintained by hand in a separate document.  
No module may query another module's database tables directly; cross-module data access goes through that module's service layer / API, even within the monolith, to keep the later microservice-extraction path (Section 4.4) realistic.  
## 4. Backend Architecture — Django
### 4.1 Application Structure
The backend is a single Django project composed of one Django app per BRD module, plus shared/core apps. This keeps ownership boundaries clear while avoiding premature microservice complexity.  
Django App  
Responsibility  
core  
Facility/department model, base audit-log mixin, base permission classes, shared utilities  
accounts  
User accounts, authentication, MFA, role/permission assignment (the RBAC engine from BRD Section 8)  
patients  
Patient Management module  
appointments  
Appointments & Queue Management  
opd  
OPD / Clinical Management  
inpatient  
Inpatient / Ward Management  
nursing  
Nursing Management  
laboratory  
Laboratory Information System (LIS)  
radiology  
Radiology / Imaging  
pharmacy  
Pharmacy Management  
billing  
Billing & Revenue Management  
insurance  
Insurance / Claims Management  
bloodbank  
Blood Bank  
emergency  
Emergency / Casualty  
theatre  
Theatre / Operating Room  
ambulance  
Ambulance Management  
inventory  
Inventory & Procurement  
hr  
HR & Staff Management  
finance  
Finance & Accounting  
reporting  
Administration & Analytics — read-only aggregation layer over every other app  
notifications  
SMS / WhatsApp / Email / push dispatch, wraps the Notification Engine actor from the BRD  
integrations  
M-Pesa (Daraja), Insurance APIs, future PACS/DICOM and accounting-system connectors  
audit  
Central audit log store and query API, consumed via the audit-log mixin in core  
### 4.2 API Layer — Django REST Framework
Every app exposes a versioned REST API under /api/v1/<app>/... — versioning is in the URL, not a header, for cache-ability and debuggability.  
Serializers are the single source of truth for API shape; DRF's schema generation (drf-spectacular) produces the OpenAPI spec automatically — it is never hand-maintained.  
Pagination is cursor-based for high-volume lists (patient timeline, audit log) and page-number-based for bounded lists (department list, role list).  
Standard error envelope across every endpoint: { "error": { "code": "...", "message": "...", "fields": {...} } } — the frontend never has to special-case error shape per module.  
Idempotency keys are required on financially significant POST endpoints (payment capture, refund, claim submission) to make retries from a flaky mobile connection safe.  
### 4.3 Authentication & Authorization
Authentication: JWT access + refresh token pair (djangorestframework-simplejwt), short-lived access token (15 min), longer-lived refresh token (7 days for web, 30 days for mobile with biometric re-auth).  
Authorization: custom DRF permission classes resolve the user's effective permission set (role → permissions, scoped by facility/department) per the BRD's module.resource.action model, evaluated on every request — never cached client-side as the source of truth.  
MFA: TOTP-based (e.g. Google Authenticator-compatible) for roles flagged as privileged in the BRD permission matrices (Administrator, Finance Manager, IT Administrator, Medical Director, Insurance Officer).  
"Break-glass" emergency access (BRD Section 7.3): implemented as a distinct, heavily audited permission grant with mandatory reason capture and automatic expiry, never a standing permission.  
### 4.4 Async Processing — Celery & Django Channels
Celery + Redis broker handles: SMS/WhatsApp/email dispatch, M-Pesa callback processing, claim submission to insurers, scheduled jobs (reorder-level checks, credential-expiry checks, appointment reminders), and report generation.  
Django Channels (WebSockets) powers real-time features that the UI in Section 8 of the Solution Spec depends on: the live queue display, live bed-status map, and critical lab-value alerts — polling is treated as a fallback, not the primary mechanism, given clinical urgency.  
Celery Beat schedules recurring jobs: nightly reconciliation checks, expiry alerts (blood units, drug stock, staff licenses), and appointment reminder dispatch.  
### 4.5 Path to Service Extraction
The modular-monolith structure in Section 4.1 is deliberately chosen so that a high-load module — most likely Laboratory, Billing, or Notifications — can be extracted into its own deployable service later without a rewrite, provided the "no cross-app direct DB access" rule in Section 3.5 has been followed. This is a Phase 3+ consideration, not a Phase 1 task, and is documented here so early architectural decisions don't foreclose it.  
## 5. Web Frontend Architecture — React
### 5.1 Application Structure
The web console (shown in the reference UI: sidebar navigation, card-based dashboard, tabbed patient profile, split-panel clinical workflows) is a single React SPA serving every staff role, with UI rendered conditionally based on the logged-in user's role and permissions — not a separate build per role.  
Routing: React Router, with route-level guards that check permissions before rendering (a route the user can't access redirects rather than renders-then-blocks).  
State management: React Query (TanStack Query) for all server state (patients, appointments, lab results, etc.) — no manual caching/refetching logic per screen. Redux Toolkit (or Zustand) is reserved for genuine client-only UI state (active tab, sidebar collapse, in-progress consultation draft).  
Component library: a shared internal design-system package (buttons, cards, tables, status badges, the bed-grid component, the queue-list component) consumed by every module screen, so the visual consistency in the reference UI is enforced structurally, not by convention.  
Forms: a schema-driven form library (e.g. React Hook Form + Zod) so validation rules are defined once and shared between the OPD consultation form, admission form, and similar structured clinical inputs.  
### 5.2 Real-Time Elements
The appointment queue panel, the bed-status grid, and critical lab-alert banners subscribe to WebSocket channels (Section 4.4) rather than polling, so a receptionist's queue view and a nurse's bed map update live without a manual refresh.  
### 5.3 Offline Tolerance (Web)
Full offline support is not targeted for the web console in Phase 1 — but in-progress clinical documentation (OPD consultation draft, nursing notes) must persist to local storage and recover from a dropped connection or accidental tab close, per the BRD's OPD edge case on interrupted consultations.  
## 6. Mobile Architecture — React Native
### 6.1 Application Structure
FDO Health (patient-facing) is the first mobile app, matching the reference UI's three mobile screens (Home, Appointments, Lab Results, Profile — bottom tab navigation). The Doctor/Clinician and Hospital Staff apps referenced in the BRD's Phase 4 scope reuse the same React Native codebase and shared component library, differing in navigation structure and permissions rather than being separate technology stacks.  
Navigation: React Navigation with a bottom tab navigator matching the reference UI (Home, Appointments, Results, Profile), each tab a stack navigator for its own drill-down screens.  
State/data: React Query for server state, mirroring the web app's pattern, so API-consumption logic is conceptually shared even though the codebases are separate.  
Local storage: encrypted on-device storage (e.g. react-native-keychain for tokens, MMKV/SQLite for cached appointment/result data) to support the offline-tolerant patterns in Section 6.2.  
Push notifications: Firebase Cloud Messaging for appointment reminders, lab-result-ready alerts, and prescription-refill notifications — dispatched from the notifications Django app (Section 4.1).  
Biometric authentication (fingerprint/face) as a fast re-auth path after the initial login, given patients will open this app briefly and repeatedly.  
### 6.2 Offline Tolerance (Mobile)
Previously loaded appointments, lab results, and profile data remain viewable when offline, clearly marked as "last synced at [time]".  
Booking actions taken offline are queued locally and submitted on reconnect using the idempotency-key pattern from Section 4.2, with a clear pending state shown to the patient rather than a silent retry.  
### 6.3 App Store & Distribution
Android via Google Play, iOS via the App Store, both behind a staged rollout (internal testing → closed beta → production) per release, not a direct-to-production release process.  
## 7. API Design Standards
Standard  
Rule  
Versioning  
URL-based (/api/v1/...); breaking changes require a new version, not a silent contract change  
Resource naming  
Plural nouns, kebab/snake-case matching Django convention (e.g. /patients/, /lab-orders/)  
Auth  
Bearer JWT in the Authorization header for every authenticated request  
Pagination  
Cursor-based for large/growing lists; explicit page size cap (max 100)  
Filtering & search  
Query-param based, consistent filter naming across modules (e.g. ?status=, ?facility=, ?date_from=)  
Error format  
Single envelope shape (Section 4.2) across all endpoints, including validation errors  
Idempotency  
Required via Idempotency-Key header on financial and clinical-order POST endpoints  
Documentation  
Auto-generated OpenAPI 3.0 spec (drf-spectacular), published at /api/schema/ and rendered via Swagger UI for internal use  
Rate limiting  
Per-user and per-IP throttling on authentication and public-facing (patient portal) endpoints  
## 8. Data Architecture
### 8.1 Database
PostgreSQL as the system of record — chosen for strong relational integrity guarantees, which matter more here than in most domains given the clinical and financial consequences of a bad write.  
Every core table includes: id (UUID, not sequential integer, to avoid enumeration/guessing across facilities), facility_id, created_at, updated_at, created_by, updated_by, and — for clinical/financial tables — a soft-delete deleted_at rather than destructive deletes, per the BRD's record-versioning requirement.  
Row-level scoping by facility_id is enforced at the query layer (custom Django manager), not left to individual view logic to remember.  
Read replicas serve the reporting/analytics app so heavy aggregate queries (BRD Section 6.18 dashboards) never compete with transactional OPD/billing writes.  
### 8.2 Caching & Session Store
Redis serves three distinct purposes and should be provisioned/monitored as such: Celery broker/result backend, Django Channels layer for WebSockets, and application-level caching (e.g. dashboard aggregate results, permission-set lookups) with explicit short TTLs on anything clinically sensitive.  
### 8.3 Object Storage
S3-compatible object storage (AWS S3 or equivalent) for patient photos, uploaded documents, lab/imaging attachments, and generated PDFs (invoices, reports) — never stored on local application-server disk, to keep app servers stateless per Section 3.2.  
### 8.4 Audit Trail
A dedicated audit app (Section 4.1) records every create/update/delete on clinical and financial models: actor, timestamp, model, record id, field-level diff, and the request's facility/IP context — queryable independently of the source module, so an audit doesn't require trusting the module being audited.  
## 9. Integration Requirements
Integration  
Purpose  
Implementation Notes  
M-Pesa (Safaricom Daraja API)  
Payment collection & confirmation  
STK Push for cashier-initiated collection; callback webhook processed asynchronously via Celery; reconciliation job matches Daraja transaction IDs to invoices nightly  
SMS / WhatsApp Gateway  
Appointment reminders, notifications, critical alerts  
Abstracted behind the notifications app so the underlying provider (e.g. Africa's Talking, Twilio) can be swapped without touching calling code  
Insurance Company APIs  
Eligibility verification, pre-authorization, claim submission  
Per-insurer adapter pattern in the integrations app, since API shape will differ materially by insurer; a manual-fallback path is required per the BRD's insurance edge cases  
Email  
Reports, statements, password reset, patient communication  
Transactional email provider (e.g. SES/SendGrid), templated via the notifications app  
PACS / DICOM (future)  
Radiology image storage & retrieval  
Not built in Phase 1–2; interim manual image upload/attachment per the BRD's radiology edge case  
Accounting System (future/optional)  
General ledger sync  
Preferred as an integration (e.g. export/API sync) rather than rebuilding a full GL, per the BRD's Finance & Accounting module recommendation  
## 10. Security Requirements
Transport security: TLS everywhere, HSTS enabled, no mixed content.  
Secrets management: environment-injected via a secrets manager (not committed to source, not baked into container images).  
Dependency hygiene: automated vulnerability scanning on every build (both Python and JavaScript dependency trees), with a policy of no critical-severity vulnerabilities in production.  
Input validation: server-side validation is authoritative on every endpoint — client-side validation is a UX convenience, never the security boundary.  
File upload handling: type/size validation, virus scanning on ingest for any uploaded document (lab attachments, HR documents, procurement invoices) before it reaches object storage.  
Penetration testing: required before the first production go-live, and after any major architectural change (e.g. the multi-branch rollout in Phase 3).  
Incident response: a documented runbook for a suspected data breach, aligned to the Kenya Data Protection Act's notification obligations.  
## 11. DevOps & Infrastructure
### 11.1 Environments
Environment  
Purpose  
Local  
Individual developer machines, Docker Compose mirroring production services  
Development  
Shared integration environment, auto-deployed from the main development branch  
Staging  
Production-like environment for UAT and pre-release verification, using anonymized data  
Production  
Live environment serving real facilities and patient data  
### 11.2 Containerization & Orchestration
Docker images for the Django backend, Celery workers, and the React web build (served via Nginx); a container registry stores versioned, immutable images per release.  
Orchestration via a managed Kubernetes service (or a simpler managed-container platform for Phase 1, e.g. AWS ECS) — the recommendation is to start with the simplest platform that meets the NFRs in Section 3 and move to Kubernetes only when multi-facility scale actually requires it, not pre-emptively.  
### 11.3 CI/CD
Every pull request runs: linting, unit tests, dependency vulnerability scan, and a build check for both backend and frontend.  
Merges to the main branch auto-deploy to Development; promotion to Staging and Production is a deliberate, approved step, never automatic for a hospital-critical system.  
Database migrations run as a distinct, reviewed step in the pipeline — never auto-applied silently alongside an application deploy.  
### 11.4 Monitoring, Logging & Alerting
Centralized structured logging (not scattered print/console statements) from Django, Celery, and both frontends' error boundaries.  
Application performance monitoring against the targets in Section 3.1, with alerting when p95 latency or error rate breaches threshold.  
Uptime monitoring on every externally facing endpoint, with on-call alerting for the clinically critical paths (authentication, OPD, lab, billing, patient portal).  
### 11.5 Backup & Disaster Recovery
Automated daily database backups with point-in-time recovery capability, tested via a periodic restore drill — an untested backup is not a backup.  
Documented Recovery Time Objective (RTO) and Recovery Point Objective (RPO) targets, agreed with the business before go-live — proposed starting point: RTO 4 hours, RPO 1 hour for Phase 1, tightened as the platform becomes more clinically load-bearing.  
## 12. Testing Strategy
Layer  
Approach  
Owner  
Unit tests  
pytest for Django (models, serializers, permission classes); Jest/React Testing Library for both React and React Native components  
Engineering  
Integration tests  
DRF APIClient-based tests covering full request/response cycles per endpoint, including permission-denial cases  
Engineering  
End-to-end tests  
Playwright/Cypress for the web console's critical flows (registration → OPD → billing); Detox for the mobile app's critical flows (login → book appointment)  
QA / Engineering  
Load testing  
Simulated concurrent-user load against the targets in Section 3.1, run before major releases and before any new facility onboarding at scale  
Engineering  
Security testing  
Automated SAST/dependency scanning in CI; manual penetration test pre-launch and periodically thereafter  
Engineering / External  
User acceptance testing (UAT)  
Structured walkthroughs of the BRD's user journeys with real hospital staff, in the Staging environment, before each major release  
Product / Clinical stakeholders  
## 13. Development Standards
Git workflow: trunk-based development with short-lived feature branches, pull-request review required before merge to main — no direct commits to main.  
Code style: enforced via automated linting/formatting (e.g. Black + isort + flake8 for Python, ESLint + Prettier for JavaScript/TypeScript) as a CI gate, not a matter of individual preference.  
TypeScript is the default for both React and React Native code — the clinical-safety stakes of this domain make compile-time type safety worth the overhead.  
Every PR includes or updates: relevant tests, and, for API changes, the OpenAPI schema (auto-generated, but the PR author confirms it reflects the intended contract).  
Architectural Decision Records (ADRs) are written for any decision that changes the assumptions in this document (e.g. choosing a different message queue, moving a module to its own service) so the reasoning isn't lost to institutional memory.  
Appendix A: Technology Stack Summary  
Layer  
Technology  
Backend framework  
Django + Django REST Framework (Python)  
Web frontend  
React + TypeScript  
Mobile frontend  
React Native + TypeScript  
Database  
PostgreSQL (primary + read replica)  
Cache / broker / real-time  
Redis (Celery broker, Channels layer, application cache)  
Async task processing  
Celery + Celery Beat  
Real-time transport  
Django Channels (WebSockets)  
Object storage  
S3-compatible object storage  
Containerization  
Docker; orchestration via managed ECS/Kubernetes  
Payments  
M-Pesa Daraja API (STK Push + callback)  
Notifications  
SMS/WhatsApp gateway + FCM push + transactional email, abstracted behind the notifications app  
API documentation  
OpenAPI 3.0 via drf-spectacular  
Testing  
pytest, Jest/RTL, Playwright/Cypress, Detox  
Appendix B: Glossary  
Term  
Definition  
DRF  
Django REST Framework — the toolkit used to build the API layer on top of Django.  
JWT  
JSON Web Token — the token format used for stateless API authentication.  
RBAC  
Role-Based Access Control — see the BRD's Permission Engine (Section 8) for the full model.  
Idempotency key  
A client-generated unique key attached to a request so retrying it (e.g. after a dropped connection) never double-processes it.  
RTO / RPO  
Recovery Time Objective / Recovery Point Objective — how long recovery may take, and how much data loss is tolerable, in a disaster scenario.  
p95 latency  
The response time below which 95% of requests complete — a standard way to express performance targets that isn't skewed by outliers.  
ADR  
Architectural Decision Record — a short document capturing a significant technical decision and its rationale.  
