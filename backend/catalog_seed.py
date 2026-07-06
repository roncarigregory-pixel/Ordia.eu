"""Catalogo demo realistico (ingrosso alimentare) creato per ogni azienda alla registrazione.

Ogni prodotto ha SKU, alias, abbreviazioni comuni, formato di confezionamento e
unità di misura, così l'AI può abbinare subito il testo disordinato degli ordini reali.
Sono dati dimostrativi — completamente modificabili e sostituibili da ogni cliente.
"""

SEED_CATALOG = [
    {
        "sku": "PRD-001", "name": "Pomodori Roma", "category": "Ortofrutta",
        "unit": "cassa", "pack_size": "1 cassa = 12 kg", "price": 18.50,
        "aliases": ["pomodori", "pomodori roma", "roma", "toms"],
    },
    {
        "sku": "PRD-002", "name": "Lattuga Iceberg", "category": "Ortofrutta",
        "unit": "cassa", "pack_size": "1 cassa = 12 cespi", "price": 22.00,
        "aliases": ["iceberg", "lattuga", "insalata iceberg"],
    },
    {
        "sku": "PRD-003", "name": "Cipolle Dorate", "category": "Ortofrutta",
        "unit": "sacco", "pack_size": "1 sacco = 25 kg", "price": 15.75,
        "aliases": ["cipolle", "cipolla dorata", "cipolle bionde", "cipolla"],
    },
    {
        "sku": "PRD-004", "name": "Avocado Hass", "category": "Ortofrutta",
        "unit": "cassa", "pack_size": "1 cassa = 48 pz", "price": 42.00,
        "aliases": ["avocado", "avo", "hass", "avocadi"],
    },
    {
        "sku": "DRY-010", "name": "Farina 00", "category": "Dispensa",
        "unit": "sacco", "pack_size": "1 sacco = 25 kg", "price": 19.90,
        "aliases": ["farina", "farina 00", "farina bianca", "farina 25kg"],
    },
    {
        "sku": "DRY-011", "name": "Zucchero Semolato", "category": "Dispensa",
        "unit": "sacco", "pack_size": "1 sacco = 25 kg", "price": 24.50,
        "aliases": ["zucchero", "zucchero bianco", "semolato"],
    },
    {
        "sku": "DRY-012", "name": "Riso Basmati", "category": "Dispensa",
        "unit": "sacco", "pack_size": "1 sacco = 20 kg", "price": 38.00,
        "aliases": ["riso", "basmati", "riso lungo"],
    },
    {
        "sku": "DRY-013", "name": "Pasta Penne", "category": "Dispensa",
        "unit": "cassa", "pack_size": "1 cassa = 12 x 500g", "price": 16.20,
        "aliases": ["penne", "pasta", "penne rigate"],
    },
    {
        "sku": "DAI-020", "name": "Latte Intero", "category": "Latticini",
        "unit": "cassa", "pack_size": "1 cassa = 12 x 1L", "price": 14.40,
        "aliases": ["latte", "latte intero", "latte 1l"],
    },
    {
        "sku": "DAI-021", "name": "Mozzarella (panetto)", "category": "Latticini",
        "unit": "cassa", "pack_size": "1 cassa = 4 x 2,5 kg", "price": 68.00,
        "aliases": ["mozzarella", "mozz", "fiordilatte", "mozzarella pizza"],
    },
    {
        "sku": "DAI-022", "name": "Burro Salato", "category": "Latticini",
        "unit": "cassa", "pack_size": "1 cassa = 20 x 250g", "price": 52.00,
        "aliases": ["burro", "burro salato", "panetti di burro"],
    },
    {
        "sku": "DAI-023", "name": "Uova Grandi", "category": "Latticini",
        "unit": "vassoio", "pack_size": "1 vassoio = 30 pz", "price": 9.80,
        "aliases": ["uova", "uova grandi", "vassoio uova", "uova 30"],
    },
    {
        "sku": "MEA-030", "name": "Petto di Pollo", "category": "Carne",
        "unit": "cartone", "pack_size": "1 cartone = 10 kg", "price": 62.00,
        "aliases": ["pollo", "petto di pollo", "fettine di pollo", "petto pollo"],
    },
    {
        "sku": "MEA-031", "name": "Macinato di Manzo", "category": "Carne",
        "unit": "cartone", "pack_size": "1 cartone = 5 kg", "price": 45.50,
        "aliases": ["macinato", "macinato di manzo", "trita", "carne macinata"],
    },
    {
        "sku": "MEA-032", "name": "Salsicce di Maiale", "category": "Carne",
        "unit": "cartone", "pack_size": "1 cartone = 5 kg", "price": 33.00,
        "aliases": ["salsicce", "salsiccia", "salsicce di maiale"],
    },
    {
        "sku": "BEV-040", "name": "Cola Lattine 330ml", "category": "Bevande",
        "unit": "cassa", "pack_size": "1 cassa = 24 lattine", "price": 17.50,
        "aliases": ["cola", "coca", "lattine cola", "bibita cola"],
    },
    {
        "sku": "BEV-041", "name": "Acqua Naturale 1,5L", "category": "Bevande",
        "unit": "cassa", "pack_size": "1 cassa = 12 bottiglie", "price": 8.90,
        "aliases": ["acqua", "acqua naturale", "acqua minerale", "acqua 1.5l"],
    },
    {
        "sku": "BEV-042", "name": "Succo d'Arancia 1L", "category": "Bevande",
        "unit": "cassa", "pack_size": "1 cassa = 8 x 1L", "price": 21.00,
        "aliases": ["succo", "succo d'arancia", "succo arancia"],
    },
    {
        "sku": "OIL-050", "name": "Olio Extravergine d'Oliva", "category": "Oli",
        "unit": "cassa", "pack_size": "1 cassa = 4 x 5L", "price": 96.00,
        "aliases": ["olio", "olio evo", "extravergine", "olio d'oliva"],
    },
    {
        "sku": "OIL-051", "name": "Olio di Semi di Girasole", "category": "Oli",
        "unit": "cassa", "pack_size": "1 cassa = 4 x 5L", "price": 48.00,
        "aliases": ["olio di semi", "olio girasole", "olio per frittura"],
    },
    {
        "sku": "FRZ-060", "name": "Patatine Fritte Surgelate", "category": "Surgelati",
        "unit": "cassa", "pack_size": "1 cassa = 4 x 2,5 kg", "price": 29.00,
        "aliases": ["patatine", "patatine fritte", "patate surgelate", "fries"],
    },
    {
        "sku": "FRZ-061", "name": "Piselli Surgelati", "category": "Surgelati",
        "unit": "cassa", "pack_size": "1 cassa = 4 x 2,5 kg", "price": 24.00,
        "aliases": ["piselli", "piselli surgelati", "pisellini"],
    },
    {
        "sku": "CND-070", "name": "Pomodori Pelati (latta)", "category": "Conserve",
        "unit": "cassa", "pack_size": "1 cassa = 12 x 400g", "price": 13.20,
        "aliases": ["pelati", "pomodori pelati", "pomodoro in scatola", "latte pomodoro"],
    },
    {
        "sku": "CND-071", "name": "Ceci (latta)", "category": "Conserve",
        "unit": "cassa", "pack_size": "1 cassa = 12 x 400g", "price": 14.60,
        "aliases": ["ceci", "ceci in scatola", "ceci lessati"],
    },
    {
        "sku": "BAK-080", "name": "Panini per Hamburger", "category": "Panetteria",
        "unit": "cassa", "pack_size": "1 cassa = 48 panini", "price": 19.00,
        "aliases": ["panini", "panini hamburger", "buns", "pane per hamburger"],
    },
]
