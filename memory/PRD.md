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

## ✅ P0 completo (incl. gap nuova specifica)
- **Nuovo Ordine**: 9 canali (Testo, WhatsApp, Email, PDF, Excel, CSV, Foto, **Scansione** fotocamera, Vocale)
  + drag&drop + copia/incolla + stepper AI animato.
- **Revisione**: 2 colonne, tabella editabile, ricerca prodotto, **creazione nuovo prodotto inline**,
  aggiungi/elimina/duplica/riordina, suggerimenti AI, warning, confidenza, cronologia, **assegnatario**.
- **Esportazione**: PDF, Excel, CSV, JSON, **Email (Resend, con PDF allegato)**, **Richiesta chiarimenti via email**.
- Architettura ERP-agnostica (layer export generico) pronta per connettori futuri.

## ✅ Automazioni (P1) — verificate iter_9 (8/8 BE + 5/5 FE)
- Conferma automatica (soglia configurabile) + trattieni nuovi clienti.
- **Routing automatico**: assegna ordini da revisionare a un membro del team.
- **Richieste chiarimenti automatiche/manuali** via email (Resend).
- `GET/PUT /api/automations`, `POST /api/orders/{id}/send-email`, pagina `AutomationSetup.js`.

## 🔌 Integrazioni
- Claude Sonnet 4.6 + Whisper (Emergent LLM Key).
- **Resend** email: `RESEND_API_KEY` + `SENDER_EMAIL=onboarding@resend.dev` in backend/.env.
  ⚠️ TEST MODE: invii reali solo verso l'email dell'account Resend / `delivered@resend.dev`.
  Per la produzione: verificare un dominio su Resend e impostare `SENDER_EMAIL` sul dominio verificato.

## 🔜 Prossimo — P2 (backlog)
- **Buyer AI**: proposte di riordino per cliente, confronto fornitori.
- **Connettori ERP**: SAP, Odoo, Business Central sopra l'export generico.
- **Analytics avanzate + Forecast**: trend volumi, previsioni domanda.
- **Workflow personalizzabili**: builder di regole avanzate (oltre auto-confirm/routing attuali).
- **Produzione email**: verifica dominio Resend + mittente aziendale.

## 🧹 Debito tecnico
- `server.py` ~1750 righe → splittare in `routers/`, `services/`, `models/`.
- WhatsApp webhook: verifica HMAC X-Hub-Signature-256.
- Indice Mongo unico (company_id, external_id).

## Credenziali
Vedi `/app/memory/test_credentials.md` — demo@ordia.app / demo123 (pilot mode auto-login).

## Test reports
- iteration_6.json: P0 lifecycle (18/18 backend + frontend happy path)
- iteration_7.json: P1 (desktop 100%, mobile bug trovato)
- iteration_8.json: P1 mobile nav fix verificato (5/5)
- Suite backend: `/app/backend/tests/test_p0_lifecycle.py`
