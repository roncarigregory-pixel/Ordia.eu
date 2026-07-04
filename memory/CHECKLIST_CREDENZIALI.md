# Ordia — Checklist credenziali per andare LIVE

Raccogli questi dati e passameli: io li configuro e colleghiamo i canali reali.

## 1. Email (ingestione ordini da casella email) — IMAP
Dove: dal provider della casella ordini (es. ordini@tuaazienda.it).
Serve:
- [ ] Server IMAP (es. imap.gmail.com, imap.aruba.it) e porta (di solito 993, SSL)
- [ ] Indirizzo email + password (o "password per app" se Gmail/Google Workspace)
- [ ] (Gmail) attivare IMAP e creare una "App Password" (Account Google → Sicurezza → Password per le app)

## 2. WhatsApp Business (ingestione ordini da WhatsApp) — Meta Cloud API
Dove: Meta for Developers (developers.facebook.com) → crea un'app → prodotto "WhatsApp".
Serve:
- [ ] Numero WhatsApp Business dedicato (non usare il tuo personale)
- [ ] Phone Number ID
- [ ] WhatsApp Business Account ID
- [ ] Access Token (permanente/di sistema)
- [ ] Verify Token (una stringa a tua scelta per il webhook)
Nota: richiede un Business Manager Meta verificato. È il passo più burocratico: mettici qualche giorno.

## 3. Resend (invio email: conferme ordine, riepiloghi Bridge)
Dove: resend.com → Domains.
Serve:
- [ ] Dominio verificato (aggiungere i record DNS SPF/DKIM che Resend indica)
- [ ] API Key
- [ ] Indirizzo mittente (es. noreply@tuodominio.it)
Finché il dominio non è verificato, Resend è in TEST MODE (consegna solo alla tua casella).

## 4. Gestionale del cliente (connettore ERP) — SOLO se ha le API
Dove: dal vendor del gestionale o dal suo installatore.
Serve:
- [ ] URL base dell'istanza (cloud o interno/VPN se on-premise)
- [ ] Tipo di autenticazione + Token/API key
- [ ] Endpoint per creare ordini (dalla documentazione API)
- [ ] Liste codici: clienti, articoli/SKU, aliquote IVA (per il mapping)
Se NON ha le API: nessun problema → usiamo il Bridge (import file o apprendimento desktop), che non richiede né URL né token.

## 5. Universal Key (motore AI)
- [ ] Verificare saldo sufficiente: Profilo → Universal Key → Add Balance (o attivare auto top-up)

---
Priorità: 5 (subito) → 1 (email, più semplice) → 3 (Resend) → 2 (WhatsApp, più lungo) → 4 (per cliente).
