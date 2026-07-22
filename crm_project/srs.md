# Software Requirements Specification (SRS)

## TechNova CRM & Consultancy Management System

---

# 1. Introduction

## 1.1 Purpose

This document specifies the software requirements for the TechNova CRM & Consultancy Management System. It serves as the technical blueprint for developing the application's backend architecture, database schema, frontend routing, and security protocols.

## 1.2 Scope

The system is a unified web platform operating under a single domain. It integrates a public-facing corporate website, a secure internal CRM for agency staff, and a dedicated portal for active clients. The platform facilitates lead generation, sales conversion, project tracking, and client communication.

---

# 2. Overall Description

## 2.1 System Environment

The application operates on a decoupled architecture, unified under a single domain routing system to bypass CORS limitations.

* **Backend:** Django, Django REST Framework (DRF), Python 3.x
* **Database:** PostgreSQL
* **Frontend:** React.js (Vite), React Router v6, Tailwind CSS
* **Authentication:** JSON Web Tokens (JWT) via `djangorestframework-simplejwt`

## 2.2 User Characteristics (Roles)

The system utilizes a single unified User model with a string-enum role attribute to dictate permissions:

* **Public Visitor:** Anonymous user interacting with marketing surfaces.
* **Client:** Authenticated external user restricted to the `/portal/*` gateway.
* **Employee:** Authenticated internal user with limited read/write access to assigned tasks.
* **Admin:** Authenticated internal user with full read/write access to CRM data via the `/admin/*` gateway.

---

# 3. System Features & Functional Requirements (FR)

## 3.1 Authentication & Authorization Module

* **FR-1.1:** The system shall authenticate users via a shared `/api/auth/login/` POST endpoint.
* **FR-1.2:** The backend shall generate short-lived JWT access tokens and longer-lived refresh tokens upon successful login.
* **FR-1.3:** The frontend shall decode the JWT payload to determine the user's role and route them to either `/admin/dashboard` or `/portal/dashboard`.
* **FR-1.4:** The backend shall enforce endpoint security using custom DRF permission classes (`IsAgencyStaff`, `IsPortalClient`) to prevent unauthorized data access regardless of frontend manipulation.

## 3.2 Lead Acquisition Module

* **FR-2.1:** The system shall expose a public POST endpoint (`/api/leads/`) to capture contact form submissions.
* **FR-2.2:** The system shall validate form payloads against a cloud-based bot mitigation token (e.g., Turnstile/reCAPTCHA).
* **FR-2.3:** The system shall automatically reject payloads exceeding the designated rate limit (`AnonRateThrottle`).

## 3.3 Core CRM & Conversion Module

* **FR-3.1:** Internal staff shall be able to view, filter, and update Lead statuses (New, Contacted, Qualified, Converted).
* **FR-3.2:** Upon changing a lead status to "Converted," the system shall execute a transactional database function that:
  1. Instantiates a new User record with `role="client"`.
  2. Generates a randomized temporary password.
  3. Creates a ClientProfile linked 1:1 to the new User.

## 3.4 Project & Task Management Module

* **FR-4.1:** Admins shall be able to create Project records and link them via foreign key to a ClientProfile.
* **FR-4.2:** Employees shall be able to create Task records linked to specific projects and assign them to other internal users.
* **FR-4.3:** Clients logged into the portal shall only be able to perform GET requests on Project records where the associated `client_id` matches their decoded JWT user ID.

---

# 4. Non-Functional Requirements (NFR)

## 4.1 Security

* **Token Storage:** JWTs must be stored securely. To mitigate Cross-Site Scripting (XSS), the application will utilize HttpOnly, Secure cookies for token transport rather than standard local storage.
* **Database Integrity:** All state-changing operations (POST/PATCH/DELETE) involving financial or conversion data must be wrapped in Django atomic database transactions (`@transaction.atomic`).

## 4.2 Performance & Scalability

* **Query Optimization:** Django QuerySets fetching lists of Projects or Clients must utilize `select_related()` and `prefetch_related()` to prevent N+1 database query inefficiencies.
* **Response Time:** API endpoints serving the frontend dashboards must resolve in under 300ms under normal load.

## 4.3 Phase 5 Operations (Deferred)

* **Asynchronous Tasks:** Complex blocking operations (e.g., bulk email notifications) are deferred from standard request/response cycles. During Phase 5, these will be offloaded to a Redis broker and processed via Celery background workers.

---

# 5. Data Schema & Models (Core)

| Model Name | Key Fields | Relationships |
|------------|------------|---------------|
| **User** | `id`, `email`, `password`, `role` | Base authentication table. |
| **ClientProfile** | `company_name`, `industry`, `billing_address` | One-to-One with User (where `role='client'`). |
| **EmployeeProfile** | `department`, `hire_date` | One-to-One with User (where `role IN ['employee', 'admin']`). |
| **Lead** | `name`, `email`, `message`, `status`, `bot_score` | Standalone; converts to User + ClientProfile. |
| **Project** | `title`, `status`, `start_date`, `end_date` | Foreign Key to ClientProfile. |
