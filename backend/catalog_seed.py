"""Realistic food-wholesale demo catalog seeded per company on registration.

Each product carries SKU, aliases, common abbreviations, packaging format and
unit conversion so the AI can match messy real-world order text immediately.
This is demonstration data — fully editable and replaceable by each customer.
"""

SEED_CATALOG = [
    {
        "sku": "PRD-001", "name": "Roma Tomatoes", "category": "Produce",
        "unit": "case", "pack_size": "1 case = 12 kg", "price": 18.50,
        "aliases": ["roma", "plum tomatoes", "tomatoes roma", "toms roma"],
    },
    {
        "sku": "PRD-002", "name": "Iceberg Lettuce", "category": "Produce",
        "unit": "case", "pack_size": "1 case = 12 heads", "price": 22.00,
        "aliases": ["iceberg", "lettuce", "salad lettuce"],
    },
    {
        "sku": "PRD-003", "name": "Yellow Onions", "category": "Produce",
        "unit": "sack", "pack_size": "1 sack = 25 kg", "price": 15.75,
        "aliases": ["onions", "yellow onion", "brown onions", "onion"],
    },
    {
        "sku": "PRD-004", "name": "Hass Avocados", "category": "Produce",
        "unit": "case", "pack_size": "1 case = 48 ct", "price": 42.00,
        "aliases": ["avocado", "avos", "hass", "avocados"],
    },
    {
        "sku": "DRY-010", "name": "All-Purpose Flour", "category": "Dry Goods",
        "unit": "bag", "pack_size": "1 bag = 25 kg", "price": 19.90,
        "aliases": ["flour", "ap flour", "plain flour", "flour 25kg"],
    },
    {
        "sku": "DRY-011", "name": "Granulated Sugar", "category": "Dry Goods",
        "unit": "bag", "pack_size": "1 bag = 25 kg", "price": 24.50,
        "aliases": ["sugar", "white sugar", "gran sugar"],
    },
    {
        "sku": "DRY-012", "name": "Basmati Rice", "category": "Dry Goods",
        "unit": "bag", "pack_size": "1 bag = 20 kg", "price": 38.00,
        "aliases": ["rice", "basmati", "long grain rice"],
    },
    {
        "sku": "DRY-013", "name": "Penne Pasta", "category": "Dry Goods",
        "unit": "case", "pack_size": "1 case = 12 x 500g", "price": 16.20,
        "aliases": ["penne", "pasta", "penne pasta"],
    },
    {
        "sku": "DAI-020", "name": "Whole Milk", "category": "Dairy",
        "unit": "case", "pack_size": "1 case = 12 x 1L", "price": 14.40,
        "aliases": ["milk", "full cream milk", "whole milk 1l"],
    },
    {
        "sku": "DAI-021", "name": "Mozzarella Block", "category": "Dairy",
        "unit": "case", "pack_size": "1 case = 4 x 2.5 kg", "price": 68.00,
        "aliases": ["mozzarella", "mozz", "pizza cheese", "mozzarella cheese"],
    },
    {
        "sku": "DAI-022", "name": "Salted Butter", "category": "Dairy",
        "unit": "case", "pack_size": "1 case = 20 x 250g", "price": 52.00,
        "aliases": ["butter", "salted butter", "butter blocks"],
    },
    {
        "sku": "DAI-023", "name": "Large Eggs", "category": "Dairy",
        "unit": "tray", "pack_size": "1 tray = 30 ct", "price": 9.80,
        "aliases": ["eggs", "egg tray", "large eggs", "eggs 30"],
    },
    {
        "sku": "MEA-030", "name": "Chicken Breast", "category": "Meat",
        "unit": "box", "pack_size": "1 box = 10 kg", "price": 62.00,
        "aliases": ["chicken", "chicken breast", "breast fillet", "ckn breast"],
    },
    {
        "sku": "MEA-031", "name": "Beef Mince", "category": "Meat",
        "unit": "box", "pack_size": "1 box = 5 kg", "price": 45.50,
        "aliases": ["mince", "beef mince", "ground beef", "minced beef"],
    },
    {
        "sku": "MEA-032", "name": "Pork Sausages", "category": "Meat",
        "unit": "box", "pack_size": "1 box = 5 kg", "price": 33.00,
        "aliases": ["sausages", "pork sausages", "snags", "bangers"],
    },
    {
        "sku": "BEV-040", "name": "Cola 330ml Cans", "category": "Beverages",
        "unit": "case", "pack_size": "1 case = 24 cans", "price": 17.50,
        "aliases": ["cola", "coke", "cola cans", "soft drink cola"],
    },
    {
        "sku": "BEV-041", "name": "Still Water 1.5L", "category": "Beverages",
        "unit": "case", "pack_size": "1 case = 12 bottles", "price": 8.90,
        "aliases": ["water", "still water", "mineral water", "water 1.5l"],
    },
    {
        "sku": "BEV-042", "name": "Orange Juice 1L", "category": "Beverages",
        "unit": "case", "pack_size": "1 case = 8 x 1L", "price": 21.00,
        "aliases": ["oj", "orange juice", "juice orange"],
    },
    {
        "sku": "OIL-050", "name": "Extra Virgin Olive Oil", "category": "Oils",
        "unit": "case", "pack_size": "1 case = 4 x 5L", "price": 96.00,
        "aliases": ["olive oil", "evoo", "extra virgin", "oil olive"],
    },
    {
        "sku": "OIL-051", "name": "Sunflower Oil", "category": "Oils",
        "unit": "case", "pack_size": "1 case = 4 x 5L", "price": 48.00,
        "aliases": ["sunflower oil", "veg oil", "cooking oil", "oil sunflower"],
    },
    {
        "sku": "FRZ-060", "name": "French Fries", "category": "Frozen",
        "unit": "case", "pack_size": "1 case = 4 x 2.5 kg", "price": 29.00,
        "aliases": ["fries", "chips", "french fries", "frozen fries"],
    },
    {
        "sku": "FRZ-061", "name": "Frozen Peas", "category": "Frozen",
        "unit": "case", "pack_size": "1 case = 4 x 2.5 kg", "price": 24.00,
        "aliases": ["peas", "frozen peas", "green peas"],
    },
    {
        "sku": "CND-070", "name": "Chopped Tomatoes Tin", "category": "Canned",
        "unit": "case", "pack_size": "1 case = 12 x 400g", "price": 13.20,
        "aliases": ["tinned tomatoes", "canned tomatoes", "chopped toms", "tomato tins"],
    },
    {
        "sku": "CND-071", "name": "Chickpeas Tin", "category": "Canned",
        "unit": "case", "pack_size": "1 case = 12 x 400g", "price": 14.60,
        "aliases": ["chickpeas", "garbanzo", "chick peas tins"],
    },
    {
        "sku": "BAK-080", "name": "Burger Buns", "category": "Bakery",
        "unit": "case", "pack_size": "1 case = 48 buns", "price": 19.00,
        "aliases": ["buns", "burger buns", "hamburger buns", "brioche buns"],
    },
]
