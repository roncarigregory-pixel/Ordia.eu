# Ordia — Strategy & Architecture North Star

> Decisione prodotto (luglio 2026): **Il Bridge è il prodotto, non un add-on.**
> Ricevere ed esportare (Excel/CSV/PDF) non basta. Il valore categoria-defining è:
> **far apparire l'ordine dentro l'ERP del cliente con il minimo intervento umano.**
> Successo = il cliente dice: "Ricevo un ordine, ed è già dentro il mio gestionale."

## Posizionamento
- Ordia NON è un order-entry né un OMS. È **il layer AI tra richieste non strutturate e il gestionale**.
- Messaggio: "Ordia non ti fa integrare nulla. Elimina la digitazione. L'ordine appare nel tuo ERP."
- ICP #1: **back office / ufficio commerciale (ADV) di grossisti/distributori food** che ricevono ordini via WhatsApp/email/PDF/telefono. Beachhead: distributori piccolo-medi su ERP file-based (es. Danea).
- NON target primario: commerciali sul campo (già serviti da app tipo EasyOrder), ristoranti/catering (mittenti, non paganti del dolore).

## Verità di mercato (evidenze)
- La maggior parte degli ERP food IT ESPONE creazione ordini: SAP B1 (Service Layer REST), Business Central (OData v4), Mexal (Web API), TeamSystem (API key+exchange), Zucchetti Ad Hoc (REST). Danea = NO API, solo import Easyfatt-XML.
- MA nell'SMB la scrittura diretta è bloccata da: no-API (Danea), on-prem irraggiungibile da SaaS, licenza/modulo non attivo, nessun IT, mapping codici master-data.
- Quindi la creazione diretta è un TIER, non il core. Il core deve funzionare anche su no-API/on-prem/desktop.

## Architettura ibrida (un cervello, più braccia, router automatico)
```
INPUT (WhatsApp/email/PDF/Excel/foto/vocale)
  → AI Extraction + Review + Approve            (già esiste)
  → ordia.order.v1 (canonico)                   (già esiste: standardize_order)
  → AI Template Profile (LLM progetta · operatore APPROVA)   ← MOTORE
  → Renderer DETERMINISTICO (CSV/XML/Excel/Easyfatt-XML)
  → DELIVERY ROUTER (per cliente/ERP):
       • Cloud API diretta   (classe A: BC, SAP B1 cloud, TS/Zucchetti cloud)
       • Ordia Bridge        (classi B/C/D: on-prem/file-only/UI-only)
       • Browser extension   (ERP web)
       • File/SFTP/Email      (fallback universale)
```
Pilastri affidabilità: import master-data opzionale (codici cliente/SKU/IVA) + learning loop esistente.

## Ordia Bridge — spec
- **Cervello nel cloud, agente sottile e muto** (outbound-only: nessuna porta, nessun IT).
- Consegna per classe, in cascata: API locale → file+trigger import → RPA-lite auto-mappato (programming-by-demonstration) → conferma.
- **Adapter Profile** per (ERP × versione × istanza): appreso 1 volta (schema/file d'esempio/dimostrazione UI) + conferma umana su ordine di prova. Effetto rete: appreso una volta → template per tutti i clienti dello stesso ERP.
- Self-install/start/update, self-healing (AI ri-mappa + riconferma), versioning + rollback.
- **PC spento**: se l'ERP è solo su un PC spento, nulla può scrivergli → ospitare l'agente dove è già sempre acceso (NAS del cliente via container, mini-appliance, server). Fallback desktop: coda cloud + consegna all'accensione + notifica.
- **Sicurezza**: mTLS in uscita, service-account ERP a privilegi minimi, segreti in keystore, audit log, primo ordine in bozza.
- **UX**: nessuna UI locale. Solo notifiche: "3 ordini già nel tuo ERP", "1 richiede revisione".

## Moat a 10 anni
NON il transport (commodity). Il moat è: **dataset di Adapter/Template Profile ERP + learning loop** accumulati su migliaia di clienti. Il Bridge è il braccio della coda-lunga; i dati sono il cervello.
"Universale nel RISULTATO, plurale nel MECCANISMO."

## Cosa NON costruire
- ❌ RPA classico non-assistito (fragile). ❌ Connettori DB/SQL diretti. ❌ Agent Windows obbligatorio per tutti.
- ❌ 100 integrazioni ERP dedicate come core. ❌ O2C completo/EDI/inventory/forecasting (feature-parity trap).
- ❌ iPaaS proprietario (semmai listing su Make/Zapier/Power Automate).

## Rollout
- Deploy live stabile (gate #1, azione utente).
- Fase 1: **AI Template Builder + download/paste** (80% valore percepito, estende export engine, zero Bridge).
- Fase 2: SFTP/watched-folder drop + listing iPaaS.
- Fase 3: connettori cloud nativi (Business Central → SAP B1).
- Fase 4 (flagship): **Ordia Bridge** (cloud relay + agente NAS/appliance + coda-fallback), poi RPA-lite auto-configurante + browser extension.

## Ciclo di vita del Bridge — "impara prima di scrivere" (luglio 2026)
> Principio guida per i 4 rischi (fragilità RPA, fiducia, deploy, master-data):
> **l'AI propone, il sistema misura la propria confidenza e agisce solo quando è sicuro; altrimenti degrada con grazia (bozza → review → fallback) e impara dalla correzione.**

Il Bridge NON è operativo appena installato. Attraversa stati di maturità:
- `unpaired` → creato, in attesa del codice.
- `learning` (shadow) → dopo il pairing. Gli ordini approvati sono consegnati come **bozze di prova** (mai come ordini finali). Accumula segnali: formato appreso, anagrafiche sincronizzate, ordini di prova riusciti, periodo di osservazione.
- `ready` → readiness ≥ 0.85 → notifica "Bridge pronto a inserire gli ordini". L'operatore attiva.
- `active` → inserimento automatico reale.
- (pausa) → può tornare a `learning` in qualsiasi momento.

**Readiness score** (segnali reali dominano; il tempo è solo un bonus):
formato 0.35 · clienti 0.15 · prodotti 0.10 · ordini-di-prova(0..5) 0.30 · osservazione(0..7g) 0.10.
Implementato in `compute_readiness` / `recompute_readiness`. Endpoint: `GET /bridge/agents/{id}/readiness`, `POST /bridge/agents/{id}/activate` (guardato dalla soglia), `POST /bridge/agents/{id}/pause`. I job portano `mode: shadow|live`; gli ack shadow incrementano `dry_runs` e non marcano l'ordine come esportato.

