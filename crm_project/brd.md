# BUSINESS REQUIREMENTS DOCUMENT (BRD)

## Project Title
TechNova CRM & Consultancy Management System

**Version:** 2.1  
**Document Type:** Business Requirements Document (BRD)  
**Prepared By:** Project Owner / Solo Developer  
**Prepared For:** TechNova Software Consultancy (Personal Project)

### Change Log
| Version | Changes |
|---|---|
| 1.0 | Initial draft |
| 2.0 | Removed budget references. Expanded BR-01–BR-08 into testable sub-requirements. Added BR-09–BR-11. Added NFRs. Rewrote Success Criteria. |
| 2.1 | **Updated Architecture Strategy:** Locked project down to a single domain layout. Refined authentication requirements to enforce strict gateway separation between internal staff (`/admin/login`) and external clients (`/portal/login`). Added anti-spam/rate-limiting mandates to public lead forms to mitigate database degradation. |

---

# 1. Executive Summary
TechNova CRM & Consultancy Management System is a unified, single-domain web platform supporting the end-to-end operations of a software consultancy: attracting leads through a public landing page, managing sales opportunities, overseeing project delivery, coordinating employee work, and maintaining client relationships.

This is a personal/portfolio project built to demonstrate full-stack product thinking and delivery, modeled on a realistic consultancy business context.

---

# 2. Business Problem Statement
A consultancy managing inquiries, projects, and client communication through disconnected tools (email, spreadsheets, chat apps) runs into:
* No centralized customer information
* Poor visibility into sales opportunities
* Inefficient project tracking
* Limited reporting and analytics
* Difficulty monitoring employee workload
* Automated spam overhead from unprotected web forms
* Risk of losing business opportunities through dropped follow-ups

---

# 3. Business Objectives
| ID | Objective |
|---|---|
| BO-01 | Centralize all customer, project, and business information within a single platform. |
| BO-02 | Improve lead acquisition and conversion through structured sales workflows. |
| BO-03 | Increase project visibility and management effectiveness. |
| BO-04 | Enhance collaboration among admins, employees, and clients. |
| BO-05 | Provide actionable business insights through reporting and analytics. |
| BO-06 | Strengthen customer engagement and support processes. |
| BO-07 | Establish a secure, scalable digital platform that prevents cross-role data leakage. |

---

# 4. Project Scope

## In Scope
* **Corporate Website** — Home, Services, Portfolio, Blog, Contact, Request a Quote
* **CRM Platform (Internal)** — Staff Auth & Dedicated Admin Gateway, Lead Tracking, Client Management, Project Management, Task Management, Team Performance, Admin Settings
* **Client Portal (External)** — Dedicated Client Login Gateway, Project Progress Monitoring, Ticket Submission, Document Downloads

## Out of Scope (Phase 1)
* Accounting System & Payroll Processing
* Online Payment Gateway
* Mobile Application
* AI-Based Recommendation Engine
* Live Chat Support

---

# 5. Stakeholders
| Stakeholder | Responsibility |
|---|---|
| Project Owner (You) | Product direction, scope, and delivery |
| Sales Role (simulated) | Lead management workflows |
| Admin Role (simulated) | Project oversight & lead management |
| Employee Role (simulated) | Task execution |
| Client Role (simulated) | Service consumption, feedback |
| System Administrator Role | Platform administration |

---

# 8. Business Requirements

## BR-01 — Lead Management (Must)
1.1 Capture leads from website contact/quote forms automatically.
1.2 Protect public endpoints against automated script submission via bot mitigation tools.
1.3 Track lead status: New → Contacted → Qualified → Converted / Lost.
1.4 Record lead source and assign to a sales owner.
1.5 Convert a qualified lead into a distinct Client record, automatically instantiating a corresponding system `User` credential set.

## BR-02 — Customer (Client) Management (Must)
2.1 Maintain a client profile: contact info, company, industry, address.
2.2 Link a client to all associated projects, communication histories, and documents.
2.3 Authenticate client users through a secure portal environment separate from internal administrative interfaces.

## BR-03 — Project Management (Must)
3.1 Create a project linked to a client with start date, target end date, and description.
3.2 Track project status: Not Started → In Progress → On Hold → Completed.
3.3 Break a project into milestones with due dates and completion tracking.

## BR-04 — Task Management (Must)
4.1 Create tasks linked to a project, client, or lead.
4.2 Assign tasks to employees with due dates, priority tiers, and operational checklists.

## BR-08 — Security and Access Control (Must)
8.1 Role-based access control for: Visitor, Client, Employee, Admin.
8.2 Enforce strict single-domain resource isolation; internal CRM resources must be visually and algorithmically inaccessible to Client roles.
8.3 All authentication uses token-based sessions (JWT) via secure HttpOnly cookie infrastructure.

---

# 9. Non-Functional Requirements (NFR)
| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Performance | Core list views should load in under 2 seconds with up to ~5,000 records. |
| NFR-02 | Security | Passwords hashed using Django defaults; JWT access tokens short-lived (~15 min); strict CORS/XSS protections for single-domain routing; API rate limits enforced on public portals. |
| NFR-04 | Usability | Clear delineation between public, client, and admin UI views via standalone routing gateways on the same domain. 
