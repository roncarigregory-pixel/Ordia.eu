# Ordia — Kit di produzione video tutorial (60–90s)

Stile di riferimento: Stripe / Notion / Linear — pulito, moderno, ritmo veloce, testi grandi, zoom morbidi.
Formati: **16:9** (sito/presentazioni) e **9:16** (Reels/TikTok/LinkedIn/Facebook). Sottotitoli sempre.

## Script + voice-over (IT) — cronometrato ~75s
| # | Tempo | Voce narrante (VO) | Cosa si vede a schermo | Testo on-screen |
|---|-------|--------------------|------------------------|-----------------|
| 1 | 0–6s | "Ogni giorno ricevi ordini da mille canali diversi." | Apertura app Ordia — Dashboard | **Ordia** · Ordini senza digitazione |
| 2 | 6–16s | "WhatsApp, email, PDF, Excel, foto… normalmente andrebbero ridigitati a mano." | Montaggio rapido: bolla WhatsApp, email, PDF, foto | Da qualsiasi canale |
| 3 | 16–26s | "Con Ordia basta caricarli. Ci pensa l'intelligenza artificiale." | Click "Nuovo Ordine" → incolla/carica un ordine | Carica l'ordine |
| 4 | 26–40s | "L'AI legge il contenuto ed estrae cliente, articoli e quantità in pochi secondi." | Animazione "lettura" → compare l'ordine strutturato | L'AI legge tutto |
| 5 | 40–52s | "Controlli solo le righe evidenziate come incerte. Il resto è già pronto." | Vista revisione a 2 colonne, righe incerte evidenziate | Controlli solo i dubbi |
| 6 | 52–60s | "Un click su Approva…" | Zoom sul pulsante Approva → click | Approva |
| 7 | 60–70s | "…e l'ordine è pronto per il tuo gestionale. In automatico." | Stato "pronto/inviato" → transizione | Direttamente nel gestionale |
| 8 | 70–75s | "Ordia. Dagli ordini caotici agli ordini pronti." | Dashboard aggiornata + logo Ordia | **Ordia** · Provalo ora |

## Sottotitoli
File pronti: `subtitles_it.srt` (stesso testo on-screen, riga per riga). Usalo sia per 16:9 che 9:16.

## Musica
Traccia consigliata: strumentale leggera, "corporate/tech uplifting", 90–100 BPM, volume −18 dB sotto la voce.
Fonti royalty-free: Epidemic Sound, Artlist, YouTube Audio Library (cerca "minimal corporate").

## Caption social (pronte)
- **LinkedIn:** "Il tuo back office ridigita ancora gli ordini a mano? Ordia legge WhatsApp, email e PDF con l'AI e li prepara per il gestionale. Guarda come funziona in 75 secondi. #automazione #food #AI"
- **Instagram/TikTok:** "Ordini da WhatsApp → nel gestionale, senza digitare 🤯 #ordini #food #AI #automazione"
- **Facebook:** "Basta digitare ordini a mano. Ordia lo fa per te con l'intelligenza artificiale. 👇"

## Come finalizzare (1 ora, senza competenze video)
1. Usa la registrazione reale dell'app generata da Ordia (`/app/frontend/public/ordia_tutorial_16x9.*` e `_9x16`).
2. Importala in **CapCut** o **Descript**.
3. Incolla `subtitles_it.srt` (o attiva auto-caption), aggiungi la musica, e — se vuoi voce — usa una voce AI (ElevenLabs/Descript) col testo VO qui sopra.
4. Esporta 16:9 e 9:16. Sostituisci il video in `ORDIA_TUTORIAL_VIDEO` dentro `frontend/src/components/Onboarding.js`.

## Sorgente modificabile
La registrazione grezza dello schermo (senza testi bruciati) resta in `public/ordia_screencast_raw.webm`: è il tuo "sorgente" da rimontare liberamente.
