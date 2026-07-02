# Ordia — PRD & Progress

## Prodotto
Ordia è una piattaforma AI di automazione ordini per distributori all'ingrosso B2B.
Riceve ordini da testo, WhatsApp, email, PDF, Excel, CSV, immagini e vocali, li estrae con
Claude Sonnet 4.6, li abbina al catalogo prodotti e apprende dalle correzioni dell'operatore.
UI e comunicazione con l'utente: **ITALIANO**. Benchmark UX: Stripe / Linear.

## Stack
- Frontend: React + TailwindCSS + Shadcn UI + framer-motion + @dnd-kit + lucide-react
- Backend: FastAPI + MongoDB (motor), JWT auth multi-tenant
- AI: Claude Sonnet 4.6 (estrazione) + Whisper (audio) via Emergent LLM Key
- Design system: navy #0B1E3B, ai-accent indigo #6366F1, font Satoshi/Manrope/JetBrains Mono

## Ordine di priorità (deciso dall'utente): happy-path prima, poi rifinitura
Ogni milestone: funzionante, testata E2E, responsive, NO dati fake, production-ready.

## ✅ Completato

### P0 — Core Workflow (iteration_6, 100% pass)
- **Nuovo Ordine** (`NewOrder.js`): 8 canali (Testo, WhatsApp, Email, PDF, Excel, CSV, Foto, Vocale),
  drag & drop universale, stepper AI animato (framer-motion, 6 fasi).
- **Estrazione AI** (`POST /api/orders/extract` → `ingest_order`/`run_extraction`): estrae cliente,
  articoli, quantità; abbinamento catalogo + confidenza + learning loop.
- **Revisione Ordine** (`OrderReview.js`): layout 2 colonne (sorgente originale sticky | tabella
  editabile), ricerca prodotto combobox (`ProductSearch.js`), aggiungi/elimina/duplica/**riordina
  (dnd-kit)**, suggerimenti AI, warning bassa confidenza, editing cliente/data, **cronologia modifiche**.
- **Conferma** (`POST /api/orders/{id}/validate` → status validated + learning).
- **Esportazione** (`GET /api/orders/{id}/export?format=`): **PDF (reportlab), Excel (openpyxl),
  CSV, JSON** — bytes costruiti prima della mutazione stato; PDF con escaping HTML.
- **Command Center** (`Dashboard.js` + `GET /api/command-center`): riepilogo in linguaggio naturale,
  ordini da revisionare, attività recente, notifiche AI, clienti recenti — **dati reali**, niente KPI finti.

### P1 — Search, Customers, Catalog, Mobile (iteration_7 + iteration_8, 100% pass)
- **Ricerca globale** (`GlobalSearch.js` in `AppShell`, ⌘K + `GET /api/search`): clienti/ordini/prodotti.
- **Clienti** (`Customers.js` + `CustomerDetail.js`, `GET /api/customers`, `/api/customers/{name}`):
  griglia card, storico ordini, insight AI, prodotti abituali.
- **Catalogo** (`Catalog.js`): CRUD prodotti + import CSV/Excel, design allineato.
- **AppShell** ridisegnato: sidebar minimale (lucide), nav Clienti, ricerca integrata.
- **Mobile**: bottom-nav dedicata, sollevata sopra il badge piattaforma (fix iteration_8).

## 🔜 Prossimo — P2 (backlog)
- **Notifiche outbound** (P2): invio automatico conferme/chiarimenti via email quando la confidenza
  AI è bassa. ⚠️ RICHIEDE scelta provider email dall'utente (Resend / SendGrid) — BLOCCO tecnico reale.
- **Connettori ERP avanzati** (P2): SAP, Odoo, Business Central sopra il layer export generico.
- **AI Buyer Assistant** (P2): proposte di riordino, confronto fornitori.
- **Automazioni** (P2): regole su ingestion (auto-conferma sopra soglia confidenza, routing).

## 🧹 Debito tecnico (non bloccante)
- `server.py` ~1660 righe → splittare in `routers/`, `services/`, `models/`.
- WhatsApp webhook: verifica HMAC X-Hub-Signature-256 prima di credenziali Meta reali.
- Indice Mongo unico su (company_id, external_id) contro doppioni webhook.

## Credenziali
Vedi `/app/memory/test_credentials.md` — demo@ordia.app / demo123 (pilot mode auto-login).

## Test reports
- iteration_6.json: P0 lifecycle (18/18 backend + frontend happy path)
- iteration_7.json: P1 (desktop 100%, mobile bug trovato)
- iteration_8.json: P1 mobile nav fix verificato (5/5)
- Suite backend: `/app/backend/tests/test_p0_lifecycle.py`
