import re
import requests
from urllib.parse import urlparse


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
    "alexflowers.lv": {
        "out": ["not available", "out of stock", "sold out", "not in stock"],
        "in": ["add to cart", "in stock", "available", "pievienot grozam", "pievienot grozam"],
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


async def detect_alexflowers_api(url):
    """Use the public WooCommerce Store API when Cloudflare hides the product page."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None

    slug = parsed.path.rstrip("/").split("/")[-1]
    if not slug:
        return None

    base = f"{parsed.scheme}://{parsed.netloc}"
    endpoints = [
        f"{base}/wp-json/wc/store/v1/products?slug={slug}",
        f"{base}/wp-json/wc/store/v1/products?search={slug.replace('-', '%20')}",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PeonyMonitor/1.0)",
        "Accept": "application/json",
    }

    for endpoint in endpoints:
        try:
            response = await __import__("asyncio").to_thread(
                requests.get,
                endpoint,
                headers=headers,
                timeout=20,
            )

            if response.status_code != 200:
                continue

            payload = response.json()
            products = payload if isinstance(payload, list) else payload.get("products", [])

            if not products:
                continue

            # Prefer an exact slug match when the API search endpoint was used.
            product = None
            for item in products:
                if isinstance(item, dict) and item.get("slug") == slug:
                    product = item
                    break
            if product is None and len(products) == 1:
                product = products[0]
            if product is None:
                continue

            if "is_in_stock" in product:
                if product["is_in_stock"] is True:
                    return "in", "WooCommerce API: is_in_stock=true"
                if product["is_in_stock"] is False:
                    return "out", "WooCommerce API: is_in_stock=false"

            add_to_cart = product.get("add_to_cart")
            if isinstance(add_to_cart, dict):
                if add_to_cart.get("url") or add_to_cart.get("text"):
                    return "in", "WooCommerce API: add_to_cart available"

            return "unknown", "WooCommerce API не содержит однозначного статуса"

        except Exception as error:
            print("[AlexFlowers API]", endpoint, repr(error))
            continue

    return None


async def detect(page, url):
    domain = domain_from_url(url)
    rules = SITE_RULES.get(domain)
    if not rules:
        return None

    # Alex Flowers is protected by a browser challenge. The public WooCommerce
    # Store API is checked before DOM parsing so the bot does not mistake the
    # Cloudflare page for an unknown product.
    if domain == "alexflowers.lv":
        api_result = await detect_alexflowers_api(url)
        if api_result is not None:
            return api_result

    area = await find_product_area(page)
    if area is None:
        return "unknown", "Не знайдено блок конкретного товару"

    text = normalize(await area.inner_text())

    phrase = first_phrase(text, rules["out"])
    if phrase:
        return "out", phrase

    phrase = first_phrase(text, rules["in"])
    if phrase:
        return "in", phrase

    if domain == "peonyshop.com":
        if re.search(r"\b\d[\d\s.,]*\s*€", text):
            return "in", "Цена доступного варианта найдена"

    return "unknown", "Не знайдено однозначного статусу в блоці конкретного товару"
