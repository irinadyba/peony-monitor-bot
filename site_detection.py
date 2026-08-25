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
        "in": ["add to cart", "in stock", "available", "pievienot grozam"],
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
    """Read Alex Flowers stock from the public WooCommerce Store API.

    The storefront is behind a browser challenge, but WooCommerce exposes
    product stock through an unauthenticated Store API. Try the canonical
    single-product-by-slug endpoint first, then the collection endpoint.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None

    slug = parsed.path.rstrip("/").split("/")[-1]
    if not slug:
        return None

    base = f"{parsed.scheme}://{parsed.netloc}"
    endpoints = [
        f"{base}/wp-json/wc/store/v1/products/{slug}",
        f"{base}/wp-json/wc/store/v1/products",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PeonyMonitor/1.0)",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    }

    for index, endpoint in enumerate(endpoints):
        try:
            params = None if index == 0 else {"slug": slug, "per_page": 10}

            response = await __import__("asyncio").to_thread(
                requests.get,
                endpoint,
                headers=headers,
                params=params,
                timeout=20,
            )

            print(
                "[AlexFlowers API]",
                response.status_code,
                response.url,
            )

            if response.status_code != 200:
                continue

            payload = response.json()

            if index == 0:
                products = [payload] if isinstance(payload, dict) else []
            else:
                products = payload if isinstance(payload, list) else payload.get("products", [])

            if not products:
                continue

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

            # Some WooCommerce installations expose the purchase state even
            # when stock is not managed directly on the product object.
            if product.get("is_purchasable") is False:
                return "out", "WooCommerce API: is_purchasable=false"

            availability = product.get("stock_availability")
            if isinstance(availability, dict):
                availability_text = normalize(availability.get("text"))
                availability_class = normalize(availability.get("class"))

                if any(x in availability_class for x in ("outofstock", "out-of-stock", "unavailable")):
                    return "out", f"WooCommerce API: stock_availability.class={availability_class}"

                if any(x in availability_text for x in ("not available", "out of stock", "sold out")):
                    return "out", f"WooCommerce API: stock_availability.text={availability_text}"

            add_to_cart = product.get("add_to_cart")
            if isinstance(add_to_cart, dict):
                add_text = normalize(add_to_cart.get("text"))
                add_url = add_to_cart.get("url")
                if add_url or add_text:
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
