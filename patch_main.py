from pathlib import Path

path = Path("main.py")
text = path.read_text(encoding="utf-8")

marker = "# =========================================================\n# УНИВЕРСАЛЬНАЯ ПРОВЕРКА\n# =========================================================\n"

if "async def get_site_product_area(" not in text:
    insert = r'''
# =========================================================
# САЙТОСПЕЦИФИЧЕСКИЙ ОСНОВНОЙ БЛОК ТОВАРА
# =========================================================

async def get_site_product_area(
    page,
    selectors
):

    for selector in selectors:

        try:

            locator = page.locator(selector)

            count = await locator.count()

            for i in range(count):

                candidate = locator.nth(i)

                try:

                    if not await candidate.is_visible():
                        continue

                    text = await candidate.inner_text()

                    if text and len(text.strip()) >= 20:
                        return candidate

                except Exception:
                    continue

        except Exception:
            continue

    return None


async def get_h1_product_area(
    page
):

    try:

        h1 = page.locator("h1").first

        if await h1.count() == 0:
            return None

        candidate = h1

        for _ in range(8):

            candidate = candidate.locator("xpath=..")

            try:

                if not await candidate.is_visible():
                    continue

                text = await candidate.inner_text()
                lower = text.lower()

                if (
                    len(text.strip()) >= 60
                    and len(text.strip()) <= 12000
                    and (
                        "sold out" in lower
                        or "add to cart" in lower
                        or "bare root" in lower
                        or "€" in text
                    )
                ):
                    return candidate

            except Exception:
                continue

    except Exception:
        pass

    return None


async def check_rottaler_pfingstrosen(
    page
):

    area = await get_site_product_area(
        page,
        [
            ".summary",
            ".product-summary",
            ".product-info",
            ".single-product .product",
        ]
    )

    if area is None:
        return "unknown", "Не знайдено основний блок товару Rottaler Pfingstrosen"

    text = (await area.inner_text()).strip()
    lower = text.lower()

    if "nicht vorrätig" in lower:
        return "out", "Nicht vorrätig"

    if "vorrätig" in lower or "in den warenkorb" in lower:
        return "in", "Vorrätig"

    return "unknown", "Не вдалося впевнено визначити наявність Rottaler Pfingstrosen"


async def check_giessler_paeonien(
    page
):

    area = await get_site_product_area(
        page,
        [
            "[id^='cc-m-product-']",
            ".cc-shop-product",
            ".j-shop-product",
            ".cc-m-product",
        ]
    )

    if area is None:
        return "unknown", "Не знайдено основний блок товару Giessler"

    text = (await area.inner_text()).strip()
    lower = text.lower()

    if "in vermehrung" in lower:
        return "out", "in Vermehrung"

    if "nicht vorrätig" in lower or "ausverkauft" in lower:
        return "out", "Nicht vorrätig"

    if "nur noch begrenzte anzahl vorhanden" in lower:
        return "in", "nur noch begrenzte Anzahl vorhanden"

    if "vorrätig" in lower or "in den warenkorb" in lower:
        return "in", "Vorrätig"

    return "unknown", "Не вдалося впевнено визначити наявність Giessler"


async def check_paeonyworld(
    page
):

    area = await get_site_product_area(
        page,
        [
            ".summary",
            ".product-summary",
            ".product-info",
            ".single-product .product",
        ]
    )

    if area is None:
        return "unknown", "Не знайдено основний блок товару Paeony World"

    text = (await area.inner_text()).strip()
    lower = text.lower()

    if "brak w magazynie" in lower:
        return "out", "Brak w magazynie"

    if "na stanie" in lower:
        return "in", "Na stanie"

    return "unknown", "Не вдалося впевнено визначити наявність Paeony World"


async def check_peonypoland(
    page
):

    area = await get_site_product_area(
        page,
        [
            ".summary",
            ".product-summary",
            ".product-info",
            ".single-product .product",
        ]
    )

    if area is None:
        return "unknown", "Не знайдено основний блок товару Peony Poland"

    text = (await area.inner_text()).strip()
    lower = text.lower()

    if "powiadomimy cię, kiedy produkt wróci na stan" in lower:
        return "out", "Powiadomimy Cię, kiedy produkt wróci na stan"

    if "brak w magazynie" in lower:
        return "out", "Brak w magazynie"

    if "na stanie" in lower:
        return "in", "Na stanie"

    return "unknown", "Не вдалося впевнено визначити наявність Peony Poland"


async def check_peonyshop(
    page
):

    area = await get_h1_product_area(page)

    if area is None:
        return "unknown", "Не знайдено основний блок товару Peonyshop"

    text = (await area.inner_text()).strip()
    lower = text.lower()

    if "sold out" in lower:
        return "out", "Sold Out!"

    if "add to cart" in lower:
        return "in", "Add to Cart"

    if re.search(r"bare root\s*:\s*€\s*[0-9]", text, re.IGNORECASE):
        return "in", "Цена доступна"

    if re.search(r"€\s*[0-9]", text):
        return "in", "Цена доступна"

    return "unknown", "Не вдалося впевнено визначити наявність Peonyshop"


'''
    text = text.replace(marker, insert + marker, 1)

old = '''        if "graefswinning.be" in url.lower():\n\n            return await check_graefswinning(\n                page\n            )\n\n        out_phrases = [\n'''

new = '''        if "graefswinning.be" in url.lower():\n\n            return await check_graefswinning(\n                page\n            )\n\n        if "rottaler-pfingstrosen.de" in url.lower():\n\n            return await check_rottaler_pfingstrosen(\n                page\n            )\n\n        if "giessler-paeonien.de" in url.lower():\n\n            return await check_giessler_paeonien(\n                page\n            )\n\n        if "paeonyworld.pl" in url.lower():\n\n            return await check_paeonyworld(\n                page\n            )\n\n        if "peonypoland.pl" in url.lower():\n\n            return await check_peonypoland(\n                page\n            )\n\n        if "peonyshop.com" in url.lower():\n\n            return await check_peonyshop(\n                page\n            )\n\n        out_phrases = [\n'''

if old not in text:
    raise SystemExit("Universal dispatch marker not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("main.py patched")
