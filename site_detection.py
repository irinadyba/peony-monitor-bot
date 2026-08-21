import re


SITE_RULES = {
    "rottaler-pfingstrosen.de": {
        "out": ["nicht vorrätig", "ausverkauft"],
        "in": ["in den warenkorb", "vorrätig"],
    },
    "giessler-paeonien.de": {
        "out": ["in vermehrung", "nicht verfügbar", "ausverkauft"],
        "in": ["nur noch begrenzte anzahl vorhanden", "in den warenkorb", "vorrätig"],
    },
    "paeonyworld.pl": {
        "out": ["brak w magazynie", "powiadomimy cię, kiedy produkt wróci na stan"],
        "in": ["na stanie", "do koszyka", "dodaj do koszyka"],
    },
    "peonypoland.pl": {
        "out": ["powiadomimy cię, kiedy produkt wróci na stan", "brak w magazynie"],
        "in": ["na stanie", "dodaj do koszyka", "do koszyka"],
    },
    "peonyshop.com": {
        "out": ["sold out", "out of stock", "unavailable"],
        "in": ["add to cart", "in stock", "available"],
    },
}


def normalize(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def first_phrase(text, phrases):
    for phrase in phrases:
        if phrase in text:
            return phrase
    return None


def domain_from_url(url):
    match = re.search(r"https?://([^/]+)", url or "", re.I)
    if not match:
        return ""
    return re.sub(r"^www\.", "", match.group(1).lower())


async def find_product_area(page):
    """Find the DOM block belonging to the current product, not recommendations."""
    h1 = page.locator("h1").first
    try:
        if await h1.count() == 0:
            return None
    except Exception:
        return None

    selectors = [
        "xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' product ')][1]",
        "xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' summary ')][1]",
        "xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' product-info ')][1]",
        "xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' product-detail ')][1]",
        "xpath=ancestor::main[1]",
    ]

    for selector in selectors:
        try:
            candidate = h1.locator(selector).first
            if await candidate.count() == 0 or not await candidate.is_visible():
                continue
            text = await candidate.inner_text()
            if 20 <= len(text.strip()) <= 18000:
                return candidate
        except Exception:
            continue

    try:
        return h1.locator("xpath=..")
    except Exception:
        return None


async def detect(page, url):
    domain = domain_from_url(url)
    rules = SITE_RULES.get(domain)
    if not rules:
        return None

    area = await find_product_area(page)
    if area is None:
        return "unknown", "Не знайдено блок конкретного товару"

    text = normalize(await area.inner_text())

    # Negative signals have priority. A price alone never means 'in stock'.
    phrase = first_phrase(text, rules["out"])
    if phrase:
        return "out", phrase

    phrase = first_phrase(text, rules["in"])
    if phrase:
        return "in", phrase

    if domain == "peonyshop.com":
        # Peonyshop may expose availability through a priced division table.
        if re.search(r"\b\d[\d\s.,]*\s*€", text):
            return "in", "Цена доступного варианта найдена"

    return "unknown", "Не знайдено однозначного статусу в блоці конкретного товару"
