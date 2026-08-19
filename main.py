import os
import asyncio
import json
import re
import requests
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "450401868"

DATA_FILE = "products.json"
CHECK_INTERVAL = 60


def load_products():
    if not os.path.exists(DATA_FILE):
        products = {
            "1": {
                "name": "ALESIA",
                "url": "https://pivoinesriviere.com/produit/alesia/",
                "status": "out",
            },
            "2": {
                "name": "Albert CROUSSE",
                "url": "https://pivoinesriviere.com/produit/albert-crousse/",
                "status": "in",
            },
            "3": {
                "name": "2005_pink_einfach",
                "url": "https://www.paeoniamiely.com/produkt/05_pink_einfach/",
                "status": "in",
            },
            "4": {
                "name": "Elsa von Brabant_2009_07",
                "url": "https://www.paeoniamiely.com/produkt/elsa-von-brabant_2009_07/",
                "status": "out",
            },
        }

        save_products(products)
        return products

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_products(products):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            products,
            f,
            ensure_ascii=False,
            indent=2
        )


def telegram_request(method, data=None):
    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/{method}"
    )

    response = requests.post(
        url,
        data=data or {},
        timeout=30
    )

    return response.json()


def send_telegram(message):
    result = telegram_request(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        }
    )

    print("Telegram:", result)


async def get_product_name(page):
    try:
        title = await page.title()

        if title:
            title = title.strip()

            title = re.sub(
                r"\s*[-|–]\s*Pivoines Rivière.*$",
                "",
                title,
                flags=re.IGNORECASE
            )

            return title

    except Exception:
        pass

    return "Неизвестный товар"


async def check_product(page, product):
    url = product["url"]

    try:
        print("Открываю:", url)

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        text = await page.locator(
            "body"
        ).inner_text()

        text_lower = text.lower()

        # =========================================
        # ЗАЩИТА САЙТОВ / CLOUDFLARE
        # =========================================

        protection_phrases = [
            "just a moment",
            "checking your browser",
            "verify you are human",
            "cf-chl",
            "cloudflare",
        ]

        for phrase in protection_phrases:

            if phrase in text_lower:

                return (
                    "unknown",
                    "Страница защиты сайта"
                )

        # =========================================
        # PIVOINES RIVIÈRE
        # =========================================

        if "pivoinesriviere.com" in url.lower():

            out_phrases = [
                "rupture de stock",
                "épuisée pour cette année",
                "notify me when available",
            ]

            for phrase in out_phrases:

                if phrase.lower() in text_lower:

                    return (
                        "out",
                        phrase
                    )

            buttons = page.locator(
                "button, input[type='submit'], a"
            )

            for i in range(
                await buttons.count()
            ):

                element = buttons.nth(i)

                try:

                    if not await element.is_visible():
                        continue

                    element_text = (
                        await element.inner_text()
                    ).strip().lower()

                    if (
                        "ajouter au panier"
                        in element_text
                    ):

                        if await element.is_enabled():

                            return (
                                "in",
                                "Ajouter au panier доступна"
                            )

                except Exception:
                    continue

            return (
                "out",
                "Кнопка покупки недоступна"
            )

        # =========================================
        # PAEONIA MIELY
        # =========================================

        if "paeoniamiely.com" in url.lower():

            if "ausverkauft" in text_lower:

                return (
                    "out",
                    "Ausverkauft"
                )

            if "nicht verfügbar" in text_lower:

                return (
                    "out",
                    "Nicht verfügbar"
                )

            if "vorrätig" in text_lower:

                return (
                    "in",
                    "Vorrätig"
                )

            buttons = page.locator(
                "button, input[type='submit'], a"
            )

            for i in range(
                await buttons.count()
            ):

                element = buttons.nth(i)

                try:

                    if not await element.is_visible():
                        continue

                    element_text = (
                        await element.inner_text()
                    ).strip().lower()

                    if (
                        "in den warenkorb"
                        in element_text
                    ):

                        if await element.is_enabled():

                            return (
                                "in",
                                "In den Warenkorb"
                            )

                except Exception:
                    continue

            return (
                "out",
                "Товар недоступен"
            )

        # =========================================
        # GRAEFSWINNING
        # =========================================

        if "graefswinning.be" in url.lower():

            # -------------------------------------
            # ЯВНО НЕТ В НАЛИЧИИ
            # -------------------------------------

            if (
                "this variety is not available"
                in text_lower
            ):

                return (
                    "out",
                    "This variety is not available"
                )

            # -------------------------------------
            # ЯВНО ДОСТУПЕН
            # -------------------------------------

            if (
                "order now for the best selection"
                in text_lower
            ):

                return (
                    "in",
                    "Order now for the best selection"
                )

            # -------------------------------------
            # Дополнительная проверка кнопки
            # -------------------------------------

            buttons = page.locator(
                "button, input[type='submit'], a"
            )

            for i in range(
                await buttons.count()
            ):

                element = buttons.nth(i)

                try:

                    if not await element.is_visible():
                        continue

                    element_text = (
                        await element.inner_text()
                    ).strip().lower()

                    if "order now" in element_text:

                        if await element.is_enabled():

                            return (
                                "in",
                                "Order now доступна"
                            )

                except Exception:
                    continue

            return (
                "unknown",
                "Не удалось определить наличие Graefswinning"
            )

        # =========================================
        # УНИВЕРСАЛЬНЫЙ АЛГОРИТМ
        # =========================================

        out_phrases = [
            "out of stock",
            "sold out",
            "unavailable",
            "out-of-stock",
            "rupture de stock",
            "épuisé",
            "épuisée",
            "nicht verfügbar",
            "ausverkauft",
            "non disponibile",
            "esaurito",
            "нет в наличии",
            "распродано",
        ]

        for phrase in out_phrases:

            if phrase in text_lower:

                return (
                    "out",
                    phrase
                )

        in_phrases = [
            "in stock",
            "en stock",
            "available",
            "add to cart",
            "ajouter au panier",
            "add to basket",
            "add to bag",
            "in den warenkorb",
            "auf lager",
            "vorrätig",
            "disponible",
        ]

        for phrase in in_phrases:

            if phrase in text_lower:

                return (
                    "in",
                    phrase
                )

        buttons = page.locator(
            "button, input[type='submit'], a"
        )

        for i in range(
            await buttons.count()
        ):

            element = buttons.nth(i)

            try:

                if not await element.is_visible():
                    continue

                element_text = (
                    await element.inner_text()
                ).strip().lower()

                buy_words = [
                    "add to cart",
                    "add to basket",
                    "add to bag",
                    "ajouter au panier",
                    "in den warenkorb",
                    "ajouter",
                ]

                for word in buy_words:

                    if word in element_text:

                        if await element.is_enabled():

                            return (
                                "in",
                                word
                            )

            except Exception:
                continue

        return (
            "unknown",
            "Не удалось уверенно определить"
        )

    except Exception as error:

        print(
            "Ошибка проверки:",
            repr(error)
        )

        return (
            "error",
            repr(error)
        )


async def add_product(
    url,
    products,
    page
):

    temporary_product = {
        "name": "Новый товар",
        "url": url,
        "status": None,
    }

    status, reason = await check_product(
        page,
        temporary_product
    )

    name = await get_product_name(page)

    if status in (
        "unknown",
        "error"
    ):

        send_telegram(
            f"🟡 {name}\n\n"
            f"Не удалось уверенно определить наличие.\n"
            f"Причина: {reason}\n\n"
            f"{url}\n\n"
            f"Товар НЕ добавлен в мониторинг."
        )

        return

    numbers = []

    for key in products:

        try:
            numbers.append(
                int(key)
            )

        except Exception:
            pass

    product_id = (
        str(max(numbers) + 1)
        if numbers
        else "1"
    )

    products[product_id] = {
        "name": name,
        "url": url,
        "status": status,
    }

    save_products(products)

    if status == "in":

        icon = "🟢"
        state = "В НАЛИЧИИ"

    else:

        icon = "🔴"
        state = "НЕТ В НАЛИЧИИ"

    send_telegram(
        f"{icon} Добавлено!\n\n"
        f"№ {product_id}\n"
        f"{name}\n"
        f"{state}\n"
        f"{reason}\n"
        f"{url}"
    )


async def handle_message(
    message,
    products,
    page
):

    chat_id = str(
        message["chat"]["id"]
    )

    if chat_id != CHAT_ID:
        return

    text = message.get(
        "text",
        ""
    ).strip()

    if not text:
        return

    # =========================================
    # /START
    # =========================================

    if text == "/start":

        send_telegram(
            "🌸 Peony Monitor работает!\n\n"
            "Команды:\n"
            "/add — добавить страницу\n"
            "/list — список\n"
            "/remove НОМЕР — удалить товар\n"
            "/check НОМЕР — проверить сейчас\n\n"
            "Можно также просто отправить ссылку."
        )

        return

    # =========================================
    # ПРОСТАЯ ССЫЛКА БЕЗ /ADD
    # =========================================

    if (
        text.startswith("http://")
        or text.startswith("https://")
    ):

        send_telegram(
            "🔎 Получила ссылку.\n"
            "Открываю страницу и проверяю..."
        )

        await add_product(
            text,
            products,
            page
        )

        return

    # =========================================
    # /LIST
    # =========================================

    if text == "/list":

        if not products:

            send_telegram(
                "Список пуст."
            )

            return

        lines = [
            "🌸 Отслеживаемые товары:\n"
        ]

        for product_id, product in products.items():

            status = product.get(
                "status"
            )

            if status == "in":

                icon = "🟢"

            elif status == "out":

                icon = "🔴"

            else:

                icon = "🟡"

            lines.append(
                f"{icon} {product_id}. "
                f"{product['name']}\n"
                f"{product['url']}"
            )

        send_telegram(
            "\n\n".join(lines)
        )

        return

    # =========================================
    # /REMOVE
    # =========================================

    if text.startswith("/remove"):

        parts = text.split()

        if len(parts) != 2:

            send_telegram(
                "Напиши номер.\n"
                "Например: /remove 2"
            )

            return

        product_id = parts[1]

        if product_id not in products:

            send_telegram(
                "Такого номера нет."
            )

            return

        removed = products.pop(
            product_id
        )

        save_products(products)

        send_telegram(
            f"🗑 Удалён:\n"
            f"{removed['name']}"
        )

        return

    # =========================================
    # /CHECK
    # =========================================

    if text.startswith("/check"):

        parts = text.split()

        if len(parts) != 2:

            send_telegram(
                "Напиши номер.\n"
                "Например: /check 2"
            )

            return

        product_id = parts[1]

        if product_id not in products:

            send_telegram(
                "Такого номера нет."
            )

            return

        product = products[product_id]

        status, reason = await check_product(
            page,
            product
        )

        if status == "in":

            icon = "🟢"
            state = "В НАЛИЧИИ"

        elif status == "out":

            icon = "🔴"
            state = "НЕТ В НАЛИЧИИ"

        else:

            icon = "🟡"
            state = "НЕ УДАЛОСЬ ОПРЕДЕЛИТЬ"

        send_telegram(
            f"{icon} {product['name']}\n\n"
            f"{state}\n"
            f"{reason}\n\n"
            f"{product['url']}"
        )

        return

    # =========================================
    # /ADD
    # =========================================

    if text.startswith("/add"):

        parts = text.split(
            maxsplit=1
        )

        if len(parts) != 2:

            send_telegram(
                "Отправь ссылку после /add."
            )

            return

        url = parts[1].strip()

        send_telegram(
            "🔎 Получила ссылку.\n"
            "Открываю страницу и проверяю..."
        )

        await add_product(
            url,
            products,
            page
        )

        return


async def telegram_listener(
    products,
    page
):

    offset = 0

    print(
        "Telegram listener запущен."
    )

    while True:

        try:

            result = await asyncio.to_thread(
                telegram_request,
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 25,
                }
            )

            if not result.get("ok"):

                await asyncio.sleep(5)

                continue

            for update in result.get(
                "result",
                []
            ):

                offset = (
                    update["update_id"] + 1
                )

                message = update.get(
                    "message"
                )

                if message:

                    print(
                        "Telegram сообщение:",
                        message.get("text")
                    )

                    await handle_message(
                        message,
                        products,
                        page
                    )

        except Exception as error:

            print(
                "Telegram listener error:",
                repr(error)
            )

            await asyncio.sleep(5)


async def monitor_products(
    products,
    page
):

    print(
        "Мониторинг товаров запущен."
    )

    while True:

        for product_id, product in list(
            products.items()
        ):

            print()
            print(
                "================================"
            )

            print(
                "Проверка:",
                product_id,
                product["name"]
            )

            status, reason = await check_product(
                page,
                product
            )

            print(
                "STATUS:",
                status
            )

            print(
                "REASON:",
                reason
            )

            # =================================
            # UNKNOWN / ERROR
            # =================================

            if status in (
                "unknown",
                "error"
            ):

                print(
                    "Состояние не изменяем."
                )

                continue

            previous_status = product.get(
                "status"
            )

            # =================================
            # ПЕРВОЕ СОСТОЯНИЕ
            # =================================

            if previous_status is None:

                product["status"] = status

                print(
                    "Начальное состояние:",
                    status
                )

            # =================================
            # OUT -> IN
            # =================================

            elif (
                previous_status == "out"
                and status == "in"
            ):

                send_telegram(
                    f"🟢 {product['name']} "
                    f"появилась в продаже!\n\n"
                    f"{reason}\n\n"
                    f"{product['url']}"
                )

                product["status"] = "in"

            # =================================
            # IN -> OUT
            # =================================

            elif (
                previous_status == "in"
                and status == "out"
            ):

                send_telegram(
                    f"🔴 {product['name']} "
                    f"закончилась.\n\n"
                    f"{reason}\n\n"
                    f"{product['url']}"
                )

                product["status"] = "out"

            # =================================
            # БЕЗ ИЗМЕНЕНИЙ
            # =================================

            else:

                print(
                    "Состояние не изменилось."
                )

        save_products(products)

        print()
        print(
            f"Следующая проверка через "
            f"{CHECK_INTERVAL} секунд."
        )

        await asyncio.sleep(
            CHECK_INTERVAL
        )


async def main():

    print(
        "================================"
    )

    print(
        "🌸 PEONY MONITOR BOT"
    )

    print(
        "БОТ ЗАПУЩЕН"
    )

    print(
        "================================"
    )

    products = load_products()

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        monitor_page = (
            await browser.new_page()
        )

        telegram_page = (
            await browser.new_page()
        )

        try:

            await asyncio.gather(
                monitor_products(
                    products,
                    monitor_page
                ),
                telegram_listener(
                    products,
                    telegram_page
                )
            )

        finally:

            await browser.close()


asyncio.run(main())
