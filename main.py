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

# ---------------------------------------------------------
# Работа со списком товаров
# ---------------------------------------------------------

def load_products():
    if not os.path.exists(DATA_FILE):
        products = {
            "1": {
                "name": "ALESIA",
                "url": "https://pivoinesriviere.com/produit/alesia/",
                "status": None,
            }
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


# ---------------------------------------------------------
# Telegram
# ---------------------------------------------------------

def telegram_request(method, data=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"

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


# ---------------------------------------------------------
# Определение названия страницы
# ---------------------------------------------------------

async def get_product_name(page):
    try:
        title = await page.title()

        if title:
            title = title.strip()

            # Убираем типичные окончания заголовка сайта
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


# ---------------------------------------------------------
# Проверка наличия
# ---------------------------------------------------------

async def check_product(page, product):
    url = product["url"]

    try:
        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        text = await page.locator("body").inner_text()
        text_lower = text.lower()

        # -------------------------------------------------
        # Pivoines Rivière
        # -------------------------------------------------

        if "pivoinesriviere.com" in url.lower():

            out_of_stock = [
                "rupture de stock",
                "notify me when available",
                "épuisée pour cette année",
            ]

            for phrase in out_of_stock:
                if phrase.lower() in text_lower:
                    return "out", phrase

            buttons = page.locator(
                "button, input[type='submit'], a"
            )

            for i in range(await buttons.count()):
                element = buttons.nth(i)

                try:
                    if not await element.is_visible():
                        continue

                    element_text = (
                        await element.inner_text()
                    ).strip().lower()

                    if "ajouter au panier" in element_text:
                        if await element.is_enabled():
                            return "in", "Ajouter au panier доступна"

                except Exception:
                    continue

            return "out", "Кнопка покупки недоступна"

        # -------------------------------------------------
        # Универсальная проверка для других сайтов
        # -------------------------------------------------

        out_phrases = [
            "out of stock",
            "sold out",
            "unavailable",
            "not available",
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
                return "out", phrase

        in_phrases = [
            "in stock",
            "en stock",
            "available",
            "add to cart",
            "ajouter au panier",
            "add to basket",
            "add to bag",
            "auf lager",
            "disponible",
            "disponibile",
        ]

        for phrase in in_phrases:
            if phrase in text_lower:
                return "in", phrase

        # Проверяем кнопку покупки
        buttons = page.locator(
            "button, input[type='submit'], a"
        )

        for i in range(await buttons.count()):
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
                            return "in", word

            except Exception:
                continue

        return "unknown", "Не удалось уверенно определить наличие"

    except Exception as error:
        return "error", repr(error)


# ---------------------------------------------------------
# Telegram команды
# ---------------------------------------------------------

async def handle_message(message, products, page):
    chat_id = str(message["chat"]["id"])

    # Не позволяем чужим чатам управлять ботом
    if chat_id != CHAT_ID:
        return

    text = message.get("text", "").strip()

    if not text:
        return

    # -----------------------------------------------------
    # /start
    # -----------------------------------------------------

    if text == "/start":

        send_telegram(
            "🌸 Peony Monitor работает!\n\n"
            "Команды:\n"
            "/add — добавить страницу\n"
            "/list — список отслеживаемых\n"
            "/remove НОМЕР — удалить товар\n"
            "/check НОМЕР — проверить сейчас"
        )

        return

    # -----------------------------------------------------
    # /list
    # -----------------------------------------------------

    if text == "/list":

        if not products:
            send_telegram(
                "Список отслеживаемых товаров пуст."
            )
            return

        lines = ["🌸 Отслеживаемые товары:\n"]

        for product_id, product in products.items():

            status = product.get("status")

            if status == "in":
                icon = "🟢"
            elif status == "out":
                icon = "🔴"
            elif status == "unknown":
                icon = "🟡"
            else:
                icon = "⚪"

            lines.append(
                f"{icon} {product_id}. "
                f"{product['name']}\n"
                f"{product['url']}"
            )

        send_telegram("\n\n".join(lines))
        return

    # -----------------------------------------------------
    # /remove
    # -----------------------------------------------------

    if text.startswith("/remove"):

        parts = text.split()

        if len(parts) != 2:
            send_telegram(
                "Напиши номер товара.\n"
                "Например: /remove 2"
            )
            return

        product_id = parts[1]

        if product_id not in products:
            send_telegram(
                "Такого номера нет."
            )
            return

        removed = products.pop(product_id)

        save_products(products)

        send_telegram(
            f"🗑 Удалён:\n"
            f"{removed['name']}"
        )

        return

    # -----------------------------------------------------
    # /check
    # -----------------------------------------------------

    if text.startswith("/check"):

        parts = text.split()

        if len(parts) != 2:
            send_telegram(
                "Напиши номер товара.\n"
                "Например: /check 1"
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
        elif status == "unknown":
            icon = "🟡"
            state = "НЕ УДАЛОСЬ ОПРЕДЕЛИТЬ"
        else:
            icon = "⚠️"
            state = "ОШИБКА ПРОВЕРКИ"

        send_telegram(
            f"{icon} {product['name']}\n\n"
            f"{state}\n"
            f"{reason}\n\n"
            f"{product['url']}"
        )

        return

    # -----------------------------------------------------
    # /add
    # -----------------------------------------------------

    if text.startswith("/add"):

        parts = text.split(maxsplit=1)

        if len(parts) != 2:
            send_telegram(
                "Отправь ссылку после /add.\n\n"
                "Например:\n"
                "/add https://example.com/product"
            )
            return

        url = parts[1].strip()

        if not url.startswith("http://") and not url.startswith("https://"):
            send_telegram(
                "Это не похоже на ссылку."
            )
            return

        send_telegram(
            "🔎 Открываю страницу и проверяю..."
        )

        temporary_product = {
            "name": "Новый товар",
            "url": url,
            "status": None,
        }

        try:
            status, reason = await check_product(
                page,
                temporary_product
            )

            name = await get_product_name(page)

        except Exception as error:
            send_telegram(
                f"⚠️ Не удалось проверить страницу:\n"
                f"{error}"
            )
            return

        # Новый номер
        numbers = []

        for key in products:
            try:
                numbers.append(int(key))
            except Exception:
                pass

        if numbers:
            product_id = str(max(numbers) + 1)
        else:
            product_id = "1"

        products[product_id] = {
            "name": name,
            "url": url,
            "status": status,
        }

        save_products(products)

        if status == "in":
            icon = "🟢"
            state = "В НАЛИЧИИ"
        elif status == "out":
            icon = "🔴"
            state = "НЕТ В НАЛИЧИИ"
        else:
            icon = "🟡"
            state = "НЕ УДАЛОСЬ УВЕРЕННО ОПРЕДЕЛИТЬ"

        send_telegram(
            f"{icon} Добавлено!\n\n"
            f"№ {product_id}\n"
            f"{name}\n"
            f"{state}\n"
            f"{url}"
        )

        return


# ---------------------------------------------------------
# Получение сообщений Telegram
# ---------------------------------------------------------

async def telegram_listener(products, page):

    offset = 0

    print("Telegram listener запущен.")

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

            for update in result.get("result", []):

                offset = update["update_id"] + 1

                message = update.get("message")

                if message:
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


# ---------------------------------------------------------
# Постоянный мониторинг
# ---------------------------------------------------------

async def monitor_products(products, page):

    print("Мониторинг товаров запущен.")

    while True:

        for product_id, product in list(products.items()):

            print()
            print("================================")
            print(
                "Проверка:",
                product_id,
                product["name"]
            )

            status, reason = await check_product(
                page,
                product
            )

            print("STATUS:", status)
            print("REASON:", reason)

            # Ошибка не меняет состояние
            if status in ("error", "unknown"):

                print(
                    "⚠️ Состояние не изменяем."
                )

                continue

            previous_status = product.get("status")

            # Первоначальная проверка
            if previous_status is None:

                product["status"] = status

                print(
                    "Начальное состояние сохранено:",
                    status
                )

            # Появился
            elif previous_status == "out" and status == "in":

                send_telegram(
                    f"🟢 {product['name']} "
                    f"появилась в продаже!\n\n"
                    f"{product['url']}"
                )

                product["status"] = "in"

            # Закончился
            elif previous_status == "in" and status == "out":

                send_telegram(
                    f"🔴 {product['name']} "
                    f"закончилась.\n\n"
                    f"{product['url']}"
                )

                product["status"] = "out"

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

        await asyncio.sleep(CHECK_INTERVAL)


# ---------------------------------------------------------
# Запуск
# ---------------------------------------------------------

async def main():

    print("================================")
    print("🌸 PEONY MONITOR BOT")
    print("БОТ ЗАПУЩЕН")
    print("================================")

    products = load_products()

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        monitor_page = await browser.new_page()
        telegram_page = await browser.new_page()

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
