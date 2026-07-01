# Ordia — Product Requirements & Build Log

## Original Problem Statement
Ordia eliminates manual order entry. Companies rewrite orders arriving from WhatsApp, Email, PDFs,
Excel, Images, Voice Messages and Phone Calls into ERP systems. Ordia extracts orders automatically;
the operator only validates. Vision: the operating system for commercial order management.
Core workflow: Receive → Understand → Extract → Validate → Learn → Export.

## User Choices
- Inputs: unified capture for text/WhatsApp, PDF, images, Excel/CSV (+ voice added in iteration 2).
- AI model: Claude Sonnet 4.6 (via Emergent Universal LLM key).
- Auth: JWT email/password, multi-tenant (company-scoped).
- Export: CSV + JSON.
- Catalog: pre-seeded realistic food-wholesale catalog, fully editable/replaceable.
- Language: entire UI in Italian.
- Pilot mode: default entry lands inside the product on a seeded demo workspace (login stays available).

## Architecture
- Backend: FastAPI + MongoDB (Motor). Multi-tenant via `company_id` on every document. UUID string ids.
- Auth: bcrypt + JWT Bearer tokens (7-day), brute-force lockout, seeded demo user.
- Ingestion layer (single pipeline, swappable inputs): text | csv/xlsx (pandas) | pdf (pypdf) |
  image (base64 → Claude vision) | audio (OpenAI Whisper whisper-1 → transcript).
- Extraction: `run_extraction()` sends source + company catalog to Claude Sonnet 4.6, returns
  normalized structured line items with catalog match + confidence + needs_review.
- Frontend: React + Tailwind + shadcn/ui, Satoshi/Geist typography, Phosphor icons, Swiss high-contrast design.

## Personas
- Back-office / order-entry operator (primary): validates extracted orders fast.
- Ops manager / owner: monitors throughput, hours saved, accuracy.
- Sales rep: forwards customer messages to be turned into orders.

## Implemented (2026-07-01)
- JWT multi-tenant auth (register creates company + seeds catalog; login; me; lockout).
- Product catalog: CRUD + CSV/Excel import; 25-item seeded food-wholesale catalog with aliases/packaging.
- Unified New Order capture (paste text / drag-drop file) with staged extraction UI.
- AI extraction for text, CSV/Excel, PDF, image, and VOICE (Whisper → Claude).
- Order Review: source-vs-extraction split, editable line items, product re-match, add/remove, totals.
- Validate + Export (CSV & JSON download).
- Dashboard KPIs (hours saved, orders, needs-review, accuracy) + recent feed.
- Italian UI throughout.
- Pilot mode: root auto-enters seeded demo workspace; 5 realistic demo orders across statuses; `/login` reachable; toggle via REACT_APP_PILOT_MODE.
- Tested: iteration_1 (16/16 backend, full E2E) and iteration_2 (pilot + voice + regression) — all pass.

## Backlog (prioritized)
- P0: "Learning" loop — persist operator corrections as customer-specific aliases to auto-improve future matches.
- P1: Real inbound email polling (IMAP fetch + attachment parsing) & WhatsApp production webhook subscription automation.
- P1: Dedicated ERP connectors (SAP, Business Central, Zucchetti, TeamSystem, Oracle, Sage, Odoo, Dynamics) on top of ordia.order.v1.
- P1: Email invites for team members (token link) + granular per-role permission enforcement in UI.
- P2: Phone-call ingestion; per-customer price lists; analytics over time; multiple WhatsApp numbers per company UI.
- P2: Split server.py into routers/services; encrypt stored access tokens at rest.

## Implemented — Iteration 3 (2026-07-01): Onboarding & Integrations
- Setup hub (/app/setup) with live progress checklist (6 steps) and integration cards.
- Guided WhatsApp Business wizard: prerequisites → credentials → real-time Graph API validation (activates on valid creds) → test message → done (webhook URL + verify token). Graceful, localized error hints + troubleshooting.
- Email channel: inbound (forwarding address / Gmail / M365 / IMAP) + outbound SMTP, with real IMAP/SMTP validation.
- ERP export layer: provider-based & ERP-agnostic (webhook/REST; JSON/CSV/XML) with standardized `ordia.order.v1` format, real "send sample order" test, and per-order push-to-ERP.
- Team management with RBAC (owner/admin/sales/operator/warehouse/readonly); Company settings.
- WhatsApp inbound webhook auto-creates draft orders via the extraction pipeline.
- Tested: iteration_3 → 21/21 backend, full frontend E2E, all pass (1 minor ERP-save bug fixed).

## Next Tasks
- Milestone 2: real inbound email polling (IMAP fetch + attachment parsing) + WhatsApp webhook subscription automation.
- Milestone 3: dedicated ERP connector foundations (registry + mappers) on voxera.order.v1.
- Milestone 4: outbound notifications (order confirmations + low-confidence clarification requests).
- Turn off pilot mode (REACT_APP_PILOT_MODE=false) for real customer onboarding.

## Implemented — Brand + Milestone 1 (2026-07-01)
- **Brand: Ordia** (final). Domain chosen: **ordia.eu** (verified available via WHOIS EURid + RDAP; ordia.com is taken/aftermarket). Identity: evolved navy "O" ring mark, uppercase ORDIA wordmark (Satoshi), midnight-blue (#0B1E3B) + white theme, favicon (white O on navy tile), horizontal lockup asset. Demo login demo@ordia.app/demo123. (Note: briefly explored "Voxera" then reverted fully to Ordia.)
- Milestone 1 — Learning Loop (P0): every validated order teaches Voxera. Confirmed line phrases persist as company-scoped learned aliases (`learned_aliases`), merged into the extraction catalog context AND applied as deterministic high-confidence overrides so the AI never repeats a matching mistake. New "Apprendimento" page (/app/setup/learning) to view/remove rules. Verified end-to-end via curl (unknown phrase → corrected → auto-matched at 0.97+ next time).
