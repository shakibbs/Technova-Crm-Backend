# PRODUCT REQUIREMENTS DOCUMENT (PRD)

## Project Title
TechNova CRM & Consultancy Management System

**Version:** 1.1  
**Document Type:** Product Requirements Document (PRD)  
**Related Document:** TechNova_BRD_v2.1.md  
**Prepared By:** Project Owner / Solo Developer

---

# 1. Product Overview
TechNova CRM & Consultancy Management System is a full-stack web application hosted on a **single unified domain** (e.g., `youragency.com`). The application organizes three logical web environments sharing a combined Django backend and a single PostgreSQL database instance:

1. **Public Corporate Website** (`/`, `/services`, `/portfolio`) — Marketing & automated lead generation.
2. **Dedicated Internal CRM Dashboard** (`/admin/dashboard/*`) — Password-protected space for internal agency staff (Employees and Admins).
3. **Dedicated Client Portal** (`/portal/dashboard/*`) — Password-protected environment for client monitoring and support tickets.

---

# 5. Features & User Stories

## 5.1 Corporate Website & Form Security
* **User Story:** As a visitor, I want to securely submit a "Request a Quote" form without my data being exposed or the site being spammed by bots.
* **Acceptance Criteria:** 
  * Form submission sends a payload to a public Django endpoint (`/api/leads/`).
  * The endpoint is protected via an anonymous rate-limiter (`AnonRateThrottle`) and cloud-based bot mitigation (e.g., Turnstile/reCAPTCHA v3).
  * Valid submissions write to the `Lead` database table immediately.

## 5.2 Dedicated Authentication Gateways
* **User Story:** As an agency admin, I want a dedicated login interface distinct from my clients so that my administrative tools remain isolated.
* **Acceptance Criteria:**
  * CRM administrative staff log in through the `/admin/login` page layout.
  * Clients log in through the `/portal/login` page layout.
  * Both interfaces call the same token endpoint (`/api/auth/login/`), but the frontend decodes the signed JWT payload to confirm if the user's role permits entry to the route.
  * Access to internal dashboard components is protected on the frontend via React Route Guards.

---

# 6. Non-Functional Requirements (Product-Level)
* **Security & State Management:** JWT access tokens must be stored using secure client mechanisms (HttpOnly cookies where possible, or memory state with automated refresh cycling). 
* **Backend Authorization:** Frontend route restrictions are mirrored by custom Django REST Framework permission classes (`IsAgencyStaff`, `IsPortalClient`). If an authenticated user manually changes their browser URL, database queries will throw a `403 Forbidden` error unless the user possesses the matching backend role.

---

# 7. Technical Architecture

## 7.1 Stack
* **Backend:** Django + Django REST Framework
* **Auth:** `djangorestframework-simplejwt`
* **Database:** PostgreSQL
* **Frontend:** React (Vite), React Router v6, Tailwind CSS
* **Async Workers (Deferred to Phase 5):** Native Django structures utilized initially to decrease setup friction. Redis and Celery introduced during operational hardening phases for non-blocking email notification task queues.

## 7.2 Single-Domain Routing Map (Frontend)
[youragency.com]├── /                               -> Public Landing Page├── /services, /portfolio           -> Marketing & Portfolio├── /portal/login                   -> Portal Gateway for Customers├── /portal/dashboard/*             -> Protected Client View (Role: Client)├── /admin/login                    -> Dedicated Internal Staff Gateway└── /admin/dashboard/*              -> Protected CRM Dashboard (Role: Employee/Admin)
## 7.3 API Delineation & Access Control

```python
# Public Anonymous Route (Protected by Rate Limiting + Bot Captcha validation)
/api/leads/                     [POST only]

# Shared Global Auth Entrypoint
/api/auth/login/                [POST] - Returns token data + role claims

# Internal Agency Staff Routes (Enforced by DRF IsAgencyStaff Permission Class)
/api/crm/leads/                 [GET, POST, PATCH]
/api/crm/clients/               [GET, POST]
/api/crm/projects/              [GET, POST, PATCH]

# Portal Client Routes (Enforced by DRF IsPortalClient + Client ID Ownership Queries)
/api/portal/projects/           [GET] - Returns ONLY projects where client_id == request.user.id
/api/portal/tickets/            [GET, POST]
```

# 8. Data Model Overview

To allow both internal workers and external portal customers to log in securely using Django's authentication mechanism, the data model avoids isolating users in dead tables. The standard Django abstract system model is extended with a explicit role field mapping out profile behaviors.

```
       +---------------------------------------------+
       |             Custom User Model               |
       |  (id, email, password, first_name, role)     |
       +---------------------------------------------+
                              |
         +--------------------+--------------------+
         | (role == 'client')                      | (role == 'employee'/'admin')
         v                                         v
+------------------+                      +-------------------+
|  ClientProfile   |                      |  EmployeeProfile  |
|  (company, etc.) |                      |  (department)     |
+------------------+                      +-------------------+
```

Core Relational Flow:

* **User** (Contains system attributes, permissions, and string-enum roles: client, employee, admin).
* **Lead** (Holds prospective sales opportunities captured anonymously from `/api/leads/`).

**Conversion Execution:** When a Lead updates to an accepted account profile status, a transaction:

1. Instantiates a primary User profile record (with `role='client'`).
2. Spawns an associated ClientProfile instance linked one-to-one back to that new account.
3. Maps the conversion criteria into immediate live operational records (Project and tracking details).

# 10. Release Plan (Phased Build Order)

| Phase | Scope | Target Metrics & Gateways |
|-------|-------|---------------------------|
| **Phase 1 — Core CRM Framework** | Auth system integration, role definitions, Core Project & Task tracking databases. | Setup internal route definitions under `/admin/dashboard/*` and connect backend DRF filters. |
| **Phase 2 — Sales Flow Tracking** | Lead tables, manual entry dashboards, and Conversion engines. | Build backend conversion utility scripts (Lead -> User account + ClientProfile). |
| **Phase 3 — Protected Client Space** | Client Portal dashboard UI, ticket sub-systems. | Configure `/portal/login` routes and establish client-data boundary controls. |
| **Phase 4 — Marketing Surface Web Integration** | Landing page launch, contact form UI assemblies. | Secure public submission entry points with bot capture modules and rate-limit controls. |
| **Phase 5 — Ops Queue & Architecture Upgrade** | Notification systems, task queues, operational analytics. | Introduce Redis and Celery components to manage asynchronous transactional email sequences. |
