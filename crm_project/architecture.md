# TECHNICAL ARCHITECTURE SPECIFICATION (v1.0)

**Project Name:** TechNova CRM & Software Agency Suite  
**System Topology:** Decoupled Monolith (Unified Single Domain Routing)  

---

## 1. System Topology & Data Flow

TechNova uses a **Separated Frontend/Backend (Decoupled)** system design. Although both codebases are independent, they are served under a single domain using a reverse proxy to bypass CORS (Cross-Origin Resource Sharing) complexities and protect authentication state.

```
   [ Client Browser ]
           │ (HTTPS)
           ▼
   [ Nginx / Caddy Proxy ]
    /                 \
   / (Static Files)    \ (Reverse Proxy to /api/*)
  ▼                     ▼
[ React SPA ]        [ Django REST Framework ]
(Vite Build)                │
                            ├─► [ PostgreSQL DB ]
                            └─► [ Turnstile/reCAPTCHA API ] (Bot Check)
```

### 1.1 Key Network Flows

1. **Static Content Delivery:** The reverse proxy serves pre-compiled, optimized React static assets directly to the client.
2. **Dynamic Data Engine (API):** Requests routed to `/api/v1/*` are transparently proxied to the Django WSGI server (Gunicorn).
3. **Third-Party Verification:** The backend securely communicates with bot-mitigation servers (e.g., Cloudflare Turnstile) out-of-band to validate public form submissions prior to processing.

---

## 2. Backend Architecture (Django Directory Design)

The Django project follows a modular apps structure. Shared utilities, abstract models, and specific domain features are cleanly compartmentalized.

```text
technova_backend/
├── manage.py
├── requirements.txt
├── technova_core/               # Global project settings & URL router
│   ├── __init__.py
│   ├── settings.py              # Environment config, DB connection, DRF throttles
│   ├── urls.py                  # Global API route aggregator (/api/v1/)
│   └── wsgi.py                  # Server interface (Gunicorn)
└── apps/
    ├── __init__.py
    ├── accounts/                # Identity & Access Management (IAM)
    │   ├── models.py            # Custom User (with Role Enum), ClientProfile, EmployeeProfile
    │   ├── serializers.py       # User serialization, registration, profile mapping
    │   ├── permissions.py       # Custom DRF classes (IsAgencyStaff, IsPortalClient)
    │   └── views.py             # Shared login, token refresh, and profile management
    ├── marketing/               # Public Landing Surface
    │   ├── models.py            # PortfolioItem, Blog, ServiceCategory
    │   ├── views.py             # Public read-only endpoints, Portfolio views
    │   └── urls.py
    └── crm/                      # Core CRM Engine
        ├── models.py            # Lead, Deal, Project, Task, Invoice, SupportTicket
        ├── services.py          # Transition scripts (e.g., Lead conversion logic)
        ├── views.py             # Internal staff endpoints, sales dashboard queries
        └── urls.py
```

### 2.1 Backend URL Architecture

Endpoints are strictly segregated to enforce network-level security and maintain readable log outputs:

* `/api/v1/auth/` — Public token issuance, validation, and rotation.
* `/api/v1/public/` — Dynamic public marketing content (read) & Lead submission (write with rate limits).
* `/api/v1/crm/` — Protected operational tables. Strictly checked via `IsAgencyStaff` permission class.
* `/api/v1/portal/` — Client portal operations. Filtered programmatically to ensure users can only access rows matching their profile ID.

---

## 3. Frontend Architecture (React / Vite Structure)

The frontend is a lightweight Single Page Application (SPA) driven by React Router v6. It uses route guards to isolate layout wrappers.

```text
technova_frontend/
├── package.json
├── vite.config.js
├── tailwind.config.js
├── index.html
└── src/
    ├── main.jsx                 # Mounts the React application
    ├── App.jsx                  # Main Router, layout definitions, global context wrapper
    ├── index.css                # Tailwind directives & global font declarations
    ├── assets/                  # Public icons, dynamic landing page media
    ├── components/              # Shared pure UI elements (Buttons, Inputs, DataTables, Kanban)
    │   ├── ScrollReveal.jsx     # Reusable Framer Motion animation container
    │   └── RouteGuards.jsx      # ProtectedRoute (Staff), PortalRoute (Client)
    ├── context/
    │   └── AuthContext.jsx      # Global React state (Decodes JWT, tracks Roles/User details)
    ├── layouts/
    │   ├── PublicLayout.jsx     # Navbar, Footer for the software agency site
    │   ├── AdminLayout.jsx      # Heavy sidebar navigation wrapper for internal CRM
    │   └── PortalLayout.jsx     # Minimalist dashboard frame for Client portal
    ├── pages/
    │   ├── public/              # Landing, Services, Contact, Portfolio
    │   ├── admin/               # Leads Kanban, Deal Pipeline, Project Status, Finance
    │   └── portal/              # Client Dashboard, Project Progress, Ticketing
    └── services/
        └── api.js               # Axios instance with interceptors for automatic JWT attachments
```

---

## 4. Database & Storage Architecture

TechNova relies on a fully relational, ACID-compliant PostgreSQL database.

```
  +------------------+         +---------------------+
  |      users       |◄────────|   client_profiles   |
  |  (Auth Account)  | 1:1     |  (Business Metadata)|
  +------------------+         +---------------------+
           ▲                              ▲
           │ 1:1                          │ 1:N
           │                              │
  +------------------+         +---------------------+
  | employee_profiles|         |      projects       |
  | (Staff Metadata) |         | (Execution Tracker) |
  +------------------+         +---------------------+
```

### 4.1 Referential Integrity Strategy

* **System-Wide UUIDs:** Avoids sequential auto-increment integer keys (`id: 1, 2, 3...`) to shield table scales and prevent database enumeration vulnerabilities.
* **ON DELETE RESTRICT** is used on critical relationships (e.g., connecting a Project or Invoice to a ClientProfile). This ensures that client profiles containing vital financial histories can never be accidentally deleted.
* **ON DELETE CASCADE** is reserved for transient data (e.g., deleting an Invoice cascadeingly drops its matching child rows in InvoiceItems).

### 4.2 Query Optimization Principles

All core dashboard views must run optimized SQL queries through Django's ORM.

Avoid N+1 queries by pre-fetching related properties:

```python
# Correct implementation example for operational dashboards:
projects = Project.objects.select_related('client_id').prefetch_related('tasks')
```

Ensure indexes are mapped to lookup columns: `email` in the `users` and `leads` tables, and `status` fields across sales pipelines.

---

## 5. Security & Authentication Architecture

Security is structured around a "Defense in Depth" system design:

* **JWT Session Control:** Access tokens are short-lived (15 minutes) and refreshed automatically.
* **HttpOnly Cookie Transport:** To mitigate Cross-Site Scripting (XSS) attacks, authorization refresh tokens are written via secure, HTTP-only cookies that cannot be accessed by browser scripts.
* **Double-Layer Authorization:**
  * **Layer 1 (React):** Frontend layout wrappers protect user views by reading the decoded client-side JWT role profile.
  * **Layer 2 (Django):** Backend API permission hooks (`IsAgencyStaff`, `IsPortalClient`) physically block API requests if the JWT signature contains a mismatched database profile role.

---

## 6. Deployment Architecture

For high availability and performance, the application is ready to be deployed to virtual private servers (such as DigitalOcean or AWS EC2) using container-ready architecture.

* **Static File S3 / CDN Hosting:** React static assets can be offloaded to Cloudflare/AWS CloudFront for blazing-fast page loads.
* **Database Management:** Utilize managed PostgreSQL instances to automatically handle transactional database snapshots, security patches, and scaling limits.
