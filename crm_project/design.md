# SYSTEM DESIGN SPECIFICATION (v1.0)

**Project Name:** TechNova CRM & Software Agency Suite  
**Visual Identity Paradigm:** "Slate & Cyber Indigo" (Dual-Mode Continuum)  

---

## 1. Visual & Aesthetic Philosophy

The TechNova visual identity represents a strategic bridge between high-concept creative design and clinical, software-focused engineering utility.

* **The External Lens (Public Surface):** Fully dark-themed (`#0f172a`), deep, immersive, and high-contrast. This format commands authority, frames portfolio work like art, and captures creative agency prestige.
* **The Internal Lens (CRM & Portal Surfaces):** Clean, high-contrast light mode base with prominent dark navigational elements. Designed to reduce visual strain during long working hours, optimizing for high data density and clean information hierarchy.

---

## 2. Global Design Tokens (The Blueprint)

### 2.1 Color Spectrum Matrix

| Category | Token | Hex Code | System Application |
|----------|-------|----------|--------------------|
| Dark Neutral (Base) | slate-900 | `#0f172a` | Public website canvas background, core administrative sidebars |
| Dark Elevate (Card) | slate-800 | `#1e293b` | Public bento-grid cards, dark-mode input containers |
| Light Neutral (Base) | slate-50 | `#f8fafc` | CRM background canvas, workspace backdrops |
| Light Elevate (Card) | white | `#ffffff` | CRM data tables, client portal workspace cards |
| Primary Core | indigo-600 | `#4f46e5` | Core interaction buttons, system call-to-actions, active indicators |
| Accent Glow | sky-400 | `#38bdf8` | Fine structural borders, linear gradients, dynamic visual highlights |
| Status: Success | emerald-500 | `#10b981` | Closed-Won Deals, completed milestones, paid invoices, active states |
| Status: Caution | amber-500 | `#f59e0b` | Leads, pending proposal configurations, tasks in review |
| Status: Alert | rose-500 | `#f43f5e` | Lost Deals, overdue invoices, high-priority support tickets |

### 2.2 Typography Scale

* **Font Primary (Headings):** "Plus Jakarta Sans" (Geometric, clean, modern)
* **Font Secondary (Body & Data):** "Inter" (High legibility, optimized for tables)

* **Header XL (Hero Copy):** `font-heading text-5xl font-bold tracking-tight` (Line-height: 1.15)
* **Header LG (Section Headings):** `font-heading text-3xl font-semibold tracking-tight`
* **Header MD (Sub-sections/Cards):** `font-heading text-xl font-medium`
* **Body Base (Prose text):** `font-body text-base font-normal leading-relaxed text-slate-400` (Dark) or `text-slate-600` (Light)
* **Data Micro (In-Table/Labels):** `font-body text-xs font-semibold uppercase tracking-wider`

---

## 3. Core Structural Layout Blueprints

### 3.1 Public Marketing Interface (Premium Cinematic Dark)

* **Header:** Fixed transparent navigation with background blur properties (`bg-brand-dark/80 backdrop-blur-md`).
* **The Hero Section:** Center-aligned copy incorporating high-impact typography with linear-gradient text properties:

```css
bg-gradient-to-r from-white via-slate-200 to-brand-accent bg-clip-text text-transparent
```

* **Portfolio Block:** A three-column asymmetric Bento Grid array, incorporating crisp structural containers using thin borders (`border border-slate-800 hover:border-slate-700 transition-all duration-300`).

### 3.2 Internal CRM Console (High-Utility Mixed Workspace)

* **Sidebar Anchor:** Fixed left panel (`bg-brand-dark / #0f172a`, width: `w-64`) housing deep slate active lists, high-contrast white text, and vivid icon signifiers.
* **Content Canvas:** Wide viewport configuration (`bg-brand-light / #f8fafc`) featuring dynamic, white-surfaced data table grids (`bg-brand-surface / #ffffff`) bounded by clean, thin borders (`border border-slate-200`).
* **Kanban Boards:** Draggable deal lanes using smooth container states and subtle drop highlights.

---

## 4. UI Elements & State Interactions

To keep the entire platform feeling cohesive across different routes, every custom component conforms to strict functional states.

### 4.1 CTA Button Configuration (Primary)

* **Default State:** `bg-brand-primary` (`#4f46e5`), `text-white`, `rounded-lg`, `font-semibold`, `px-5 py-2.5`.
* **Hover State:** `hover:bg-indigo-700 hover:shadow-lg hover:shadow-indigo-500/20 transition-all duration-200`.
* **Active/Focus State:** `focus:ring-4 focus:ring-indigo-500/30`.

### 4.2 Interactive Input Fields

* **Default State:** Transparent (Public) or Solid White (CRM), rounded border (`rounded-lg`), thin outline (`border-slate-700` public / `border-slate-200` CRM).
* **Focus State:** Smooth transition (`transition-all duration-200`), primary border outline (`focus:border-brand-primary`), accompanied by an ambient glow drop shadow:

```css
focus:ring-4 focus:ring-brand-primary/10
```

---

## 5. Micro-Interactions & Animation Directives

Our scroll animations utilize Framer Motion to keep interactions hardware-accelerated. Animations are configured to execute only once when crossing into the viewport boundary.

### 5.1 Motion Behavior Specifications

* **Entrance Threshold:** Trigger animations when the container reaches exactly `-80px` of the user's viewport boundary (`viewport={{ once: true, margin: "-80px" }}`).
* **Transition Curves:** Avoid using stock transitions. All UI movements must use a clean, highly customized Cubic Bezier curve profile:

```javascript
ease: [0.215, 0.610, 0.355, 1.000] // Deceleration transition curve (Out-Sine equivalent)
```

* **Staggered Reveals:** For groups of elements (e.g., service listings or cards), implement child sequence delay timings (`staggerChildren: 0.15`). Each individual element reveals sequentially to guide the user's eye naturally down the page.
