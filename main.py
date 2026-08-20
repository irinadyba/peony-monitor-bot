```python
import os
import asyncio
import json
import re
import requests
from urllib.parse import urlparse
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


# =========================================================
# НАСТРОЙКИ
# =========================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "450401868"

DATA_FILE = "products.json"
CHECK_INTERVAL = 60


# =========================================================
# ТОВАРЫ
# =========================================================

def load_products():
    if not os.path.exists(DATA_FILE):
        products = {
            "1": {
                "name": "ALESIA",
                "url": "https://pivoinesriviere.com/produit/alesia",
                "status": "out",
            },
            "2": {
                "name": "Albert CROUSSE",
                "url": "https://pivoinesriviere.com/produit/albert-crousse",
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
            products = json.load(f)

        return products

    except Exception as error:
        print("Ошибка чтения products.json:", repr(error))
        return {}


def save_products(products):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                products,
                f,
                ensure_ascii=False,
                indent=2
            )
    except Exception as error:
        print("Ошибка сохранения products.json:", repr(error))


# =========================================================
# TELEGRAM API
# =========================================================

def telegram_request(method, data=None):
    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/{method}"
    )

    try:
        response = requests.post(
            url,
            data=data or {},
            timeout=30
        )

        return response.json()

    except Exception as error:
        print("Telegram API error:", repr(error))
        return {
            "ok": False,
            "error": repr(error)
        }


def send_telegram(message, reply_markup=None):
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": True,
    }

    if reply_markup is not None:
        data["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False
        )

    result = telegram_request(
        "sendMessage",
        data
    )

    print("Telegram:", result)

    return result


def edit_telegram_message(
    message_id,
    text,
    reply_markup=None
):
    data = {
        "chat_id": CHAT_ID,
        "message_id": message_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    if reply_markup is not None:
        data["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False
        )

    result = telegram_request(
        "editMessageText",
        data
    )

    print("Telegram edit:", result)

    return result


def answer_callback(callback_id):
    telegram_request(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


# =========================================================
# НАЗВАНИЕ САЙТА
# =========================================================

def get_site_name(url):
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower()

        if "paeoniamiely" in hostname:
            return "paeoniamiely"

        if "graefswinning" in hostname:
            return "graefswinning"

        if "pivoinesriviere" in hostname:
            return "pivoinesriviere"

        # Универсально:
        # от // до следующего /
        clean = re.sub(
            r"^https?://",
            "",
            url,
            flags=re.IGNORECASE
        )

        domain = clean.split("/")[0]

        domain = domain.replace("www.", "")

        return domain

    except Exception:
        return "невідомий сайт"


# =========================================================
# СТАТУС
# =========================================================

def status_icon(status):
    if status == "in":
        return "🟢"

    if status == "out":
        return "🔴"

    return "🟡"


def status_text(status):
    if status == "in":
        return "В НАЯВНОСТІ"

    if status == "out":
        return "НЕМАЄ В НАЯВНОСТІ"

    return "НЕ ВДАЛОСЯ ВИЗНАЧИТИ"


# =========================================================
# TELEGRAM КЛАВІАТУРЫ
# =========================================================

def main_menu():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🌸 Мої півонії",
                    "callback_data": "list"
                },
                {
                    "text": "➕ Додати",
                    "callback_data": "add_help"
                }
            ],
            [
                {
                    "text": "🔄 Перевірити всі",
                    "callback_data": "check_all"
                },
                {
                    "text": "🔍 Перевірити",
                    "callback_data": "check_choose"
                }
            ]
        ]
    }


def bottom_menu():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🌸 Головне меню",
                    "callback_data": "menu"
                }
            ]
        ]
    }


def product_keyboard(product_id, product):
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🛒 Товар",
                    "url": product["url"]
                },
                {
                    "text": "🔍 Перевірити",
                    "callback_data": f"check:{product_id}"
                },
                {
                    "text": "🗑 Видалити",
                    "callback_data": f"remove:{product_id}"
                }
            ],
            [
                {
                    "text": "🌸 Головне меню",
                    "callback_data": "menu"
                }
            ]
        ]
    }


def delete_confirmation_keyboard(product_id):
    return {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Так",
                    "callback_data": f"remove_confirm:{product_id}"
                },
                {
                    "text": "❌ Скасувати",
                    "callback_data": f"remove_cancel:{product_id}"
                }
            ]
        ]
    }


def choose_product_keyboard(products):
    rows = []

    for product_id, product in products.items():

        icon = status_icon(
            product.get("status")
        )

        rows.append(
            [
                {
                    "text": (
                        f"{icon} "
                        f"{product['name']}"
                    ),
                    "callback_data": (
                        f"check:{product_id}"
                    )
                }
            ]
        )

    rows.append(
        [
            {
                "text": "🌸 Головне меню",
                "callback_data": "menu"
            }
        ]
    )

    return {
        "inline_keyboard": rows
    }


# =========================================================
# НАЗВАНИЕ ТОВАРА
# =========================================================

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

            title = re.sub(
                r"\s*[-|–]\s*Graefs.*$",
                "",
                title,
                flags=re.IGNORECASE
            )

            return title.strip()

    except Exception:
        pass

    return "Невідомий товар"


# =========================================================
# БЕЗОПАСНАЯ ЗАГРУЗКА СТРАНИЦЫ
# =========================================================

async def safe_goto(page, url):

    try:

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        return True, ""

    except Exception as error:

        print(
            "Ошибка открытия страницы:",
            repr(error)
        )

        return False, repr(error)


# =========================================================
# GRAEFSWINNING
# =========================================================

async def get_main_product_area(page):

    selectors = [
        "form.cart",
        "form.variations_form",
        ".summary",
        ".product-summary",
        ".product-info",
        ".single-product",
        "main",
    ]

    for selector in selectors:

        try:

            locator = page.locator(selector)

            count = await locator.count()

            if count == 0:
                continue

            for i in range(count):

                candidate = locator.nth(i)

                try:

                    if not await candidate.is_visible():
                        continue

                    text = await candidate.inner_text()

                    if text and len(text.strip()) > 20:
                        return candidate

                except Exception:
                    continue

        except Exception:
            continue

    return None


async def check_graefswinning(page):

    product_area = await get_main_product_area(page)

    if product_area is None:
        return (
            "unknown",
            "Не знайдено основний блок товару"
        )

    try:

        product_text = await product_area.inner_text()

        product_text_lower = product_text.lower()

        # -----------------------------------------
        # НЕТ В НАЛИЧИИ
        # -----------------------------------------

        unavailable_phrases = [
            "this variety is not available",
            "this product is not available",
            "this variety is unavailable",
            "not available",
        ]

        for phrase in unavailable_phrases:

            if phrase in product_text_lower:

                return (
                    "out",
                    phrase
                )

        # -----------------------------------------
        # В НАЛИЧИИ
        # -----------------------------------------

        if (
            "order now for the best selection"
            in product_text_lower
        ):

            return (
                "in",
                "Order now for the best selection"
            )

        # -----------------------------------------
        # ADD TO CART
        # -----------------------------------------

        buttons = product_area.locator(
            "button, input[type='submit'], a"
        )

        count = await buttons.count()

        for i in range(count):

            element = buttons.nth(i)

            try:

                if not await element.is_visible():
                    continue

                element_text = (
                    await element.inner_text()
                ).strip().lower()

                if "add to cart" in element_text:

                    if await element.is_enabled():

                        return (
                            "in",
                            "Add to cart доступна"
                        )

            except Exception:
                continue

        return (
            "unknown",
            "Не вдалося впевнено визначити наявність Graefswinning"
        )

    except Exception as error:

        return (
            "error",
            repr(error)
        )


# =========================================================
# ПРОВЕРКА ТОВАРА
# =========================================================

async def check_product(page, product):

    url = product["url"]

    print(
        "Відкриваю:",
        url
    )

    ok, error_text = await safe_goto(
        page,
        url
    )

    if not ok:

        return (
            "error",
            error_text
        )

    try:

        text = await page.locator(
            "body"
        ).inner_text()

        text_lower = text.lower()

    except Exception as error:

        return (
            "error",
            repr(error)
        )

    # =====================================================
    # ЗАХИСТ САЙТУ
    # =====================================================

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
                "Сторінка захисту сайту"
            )

    # =====================================================
    # PIVOINES RIVIERE
    # =====================================================

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

        count = await buttons.count()

        for i in range(count):

            element = buttons.nth(i)

            try:

                if not await element.is_visible():
                    continue

                element_text = (
                    await element.inner_text()
                ).strip().lower()

                if "ajouter au panier" in element_text:

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

    # =====================================================
    # PAEONIA MIELY
    # =====================================================

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

        count = await buttons.count()

        for i in range(count):

            element = buttons.nth(i)

            try:

                if not await element.is_visible():
                    continue

                element_text = (
                    await element.inner_text()
                ).strip().lower()

                if "in den warenkorb" in element_text:

                    if await element.is_enabled():

                        return (
                            "in",
                            "In den Warenkorb"
                        )

            except Exception:
                continue

        return (
            "out",
            "Товар недоступний"
        )

    # =====================================================
    # GRAEFSWINNING
    # =====================================================

    if "graefswinning.be" in url.lower():

        return await check_graefswinning(
            page
        )

    # =====================================================
    # УНИВЕРСАЛЬНЫЙ АЛГОРИТМ
    # =====================================================

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

    return (
        "unknown",
        "Не вдалося впевнено визначити"
    )


# =========================================================
# ТЕКСТ ТОВАРА
# =========================================================

def product_message(product):

    status = product.get("status")

    icon = status_icon(status)

    site = get_site_name(
        product["url"]
    )

    return (
        f"{icon} {product['name']}\n"
        f"🌐 {site}\n\n"
        f"Статус: {status_text(status)}"
    )


# =========================================================
# СПИСОК
# =========================================================

def send_product_list(products):

    if not products:

        send_telegram(
            "🌸 Список відстеження порожній.",
            main_menu()
        )

        return

    send_telegram(
        "🌸 Мої півонії",
        main_menu()
    )

    for product_id, product in products.items():

        send_telegram(
            product_message(product),
            product_keyboard(
                product_id,
                product
            )
        )


# =========================================================
# ДОБАВЛЕНИЕ
# =========================================================

async def add_product(
    url,
    products,
    page
):

    temporary_product = {
        "name": "Новий товар",
        "url": url,
        "status": None,
    }

    status, reason = await check_product(
        page,
        temporary_product
    )

    name = await get_product_name(
        page
    )

    if status in (
        "unknown",
        "error"
    ):

        send_telegram(
            f"🟡 {name}\n"
            f"🌐 {get_site_name(url)}\n\n"
            f"Не вдалося впевнено визначити наявність.\n"
            f"Причина: {reason}\n\n"
            f"Товар НЕ додано до відстеження.",
            main_menu()
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

    product = products[
        product_id
    ]

    send_telegram(
        f"{status_icon(status)} Додано!\n\n"
        f"{product_message(product)}\n\n"
        f"Причина: {reason}",
        product_keyboard(
            product_id,
            product
        )
    )


# =========================================================
# CALLBACK
# =========================================================

async def handle_callback(
    callback,
    products,
    page
):

    callback_id = callback["id"]

    data = callback.get(
        "data",
        ""
    )

    message = callback.get(
        "message"
    )

    message_id = None

    if message:
        message_id = message.get(
            "message_id"
        )

    answer_callback(
        callback_id
    )

    # =====================================================
    # ГЛАВНОЕ МЕНЮ
    # =====================================================

    if data == "menu":

        if message_id:

            edit_telegram_message(
                message_id,
                "🌸 PEONY MONITOR\n\n"
                "Оберіть дію:",
                main_menu()
            )

        return

    # =====================================================
    # СПИСОК
    # =====================================================

    if data == "list":

        send_product_list(
            products
        )

        return

    # =====================================================
    # ДОБАВИТЬ
    # =====================================================

    if data == "add_help":

        send_telegram(
            "➕ Додати півонію\n\n"
            "Просто надішліть мені посилання "
            "на сторінку півонії.\n\n"
            "Я перевірю наявність і додам "
            "її до відстеження.",
            bottom_menu()
        )

        return

    # =====================================================
    # ВЫБОР ТОВАРА
    # =====================================================

    if data == "check_choose":

        if not products:

            send_telegram(
                "Список порожній.",
                main_menu()
            )

            return

        send_telegram(
            "🔍 Оберіть півонію:",
            choose_product_keyboard(products)
        )

        return

    # =====================================================
    # ПРОВЕРИТЬ ВСЕ
    # =====================================================

    if data == "check_all":

        send_telegram(
            "🔄 Починаю перевірку всіх півоній..."
        )

        for product_id, product in list(
            products.items()
        ):

            try:

                status, reason = await check_product(
                    page,
                    product
                )

                print(
                    "Ручна перевірка:",
                    product_id,
                    status,
                    reason
                )

                if status in (
                    "unknown",
                    "error"
                ):
                    continue

                product["status"] = status

            except Exception as error:

                print(
                    "Помилка ручної перевірки:",
                    repr(error)
                )

                continue

        save_products(
            products
        )

        send_telegram(
            "✅ Перевірку всіх півоній завершено.",
            main_menu()
        )

        return

    # =====================================================
    # CHECK ONE
    # =====================================================

    if data.startswith("check:"):

        product_id = data.split(
            ":",
            1
        )[1]

        if product_id not in products:

            send_telegram(
                "Півонію вже видалено.",
                main_menu()
            )

            return

        product = products[
            product_id
        ]

        send_telegram(
            f"🔍 Перевіряю:\n"
            f"{product['name']}..."
        )

        try:

            status, reason = await check_product(
                page,
                product
            )

        except Exception as error:

            status = "error"
            reason = repr(error)

        if status in (
            "unknown",
            "error"
        ):

            send_telegram(
                f"🟡 {product['name']}\n"
                f"🌐 {get_site_name(product['url'])}\n\n"
                f"Не вдалося впевнено визначити.\n"
                f"Причина: {reason}",
                product_keyboard(
                    product_id,
                    product
                )
            )

            return

        product["status"] = status

        save_products(
            products
        )

        send_telegram(
            f"{product_message(product)}\n\n"
            f"{reason}",
            product_keyboard(
                product_id,
                product
            )
        )

        return

    # =====================================================
    # REMOVE
    # =====================================================

    if data.startswith("remove:"):

        product_id = data.split(
            ":",
            1
        )[1]

        if product_id not in products:

            send_telegram(
                "Півонію вже видалено.",
                main_menu()
            )

            return

        product = products[
            product_id
        ]

        send_telegram(
            f"🗑 Видалити\n"
            f"«{product['name']}»\n"
            f"з відстеження?",
            delete_confirmation_keyboard(
                product_id
            )
        )

        return

    # =====================================================
    # REMOVE CONFIRM
    # =====================================================

    if data.startswith("remove_confirm:"):

        product_id = data.split(
            ":",
            1
        )[1]

        if product_id not in products:

            send_telegram(
                "Півонію вже видалено.",
                main_menu()
            )

            return

        removed = products.pop(
            product_id
        )

        save_products(
            products
        )

        send_telegram(
            f"🗑 {removed['name']}\n"
            f"видалено з відстеження.",
            main_menu()
        )

        return

    # =====================================================
    # REMOVE CANCEL
    # =====================================================

    if data.startswith("remove_cancel:"):

        product_id = data.split(
            ":",
            1
        )[1]

        if product_id not in products:

            send_telegram(
                "Півонію вже видалено.",
                main_menu()
            )

            return

        product = products[
            product_id
        ]

        send_telegram(
            f"❌ Видалення скасовано.\n\n"
            f"{product_message(product)}",
            product_keyboard(
                product_id,
                product
            )
        )

        return


# =========================================================
# ОБЫЧНЫЕ СООБЩЕНИЯ
# =========================================================

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

    # /start

    if text == "/start":

        send_telegram(
            "🌸 PEONY MONITOR\n\n"
            "Бот відстежує наявність півоній "
            "і повідомляє про зміни.\n\n"
            "Оберіть дію:",
            main_menu()
        )

        return

    # /list

    if text == "/list":

        send_product_list(
            products
        )

        return

    # /remove

    if text.startswith("/remove"):

        parts = text.split()

        if len(parts) != 2:

            send_telegram(
                "Напишіть номер півонії.\n"
                "Наприклад: /remove 2",
                main_menu()
            )

            return

        product_id = parts[1]

        if product_id not in products:

            send_telegram(
                "Такого номера немає.",
                main_menu()
            )

            return

        product = products[
            product_id
        ]

        send_telegram(
            f"🗑 Видалити\n"
            f"«{product['name']}»\n"
            f"з відстеження?",
            delete_confirmation_keyboard(
                product_id
            )
        )

        return

    # /check

    if text.startswith("/check"):

        parts = text.split()

        if len(parts) != 2:

            send_telegram(
                "Напишіть номер.\n"
                "Наприклад: /check 2",
                main_menu()
            )

            return

        product_id = parts[1]

        if product_id not in products:

            send_telegram(
                "Такого номера немає.",
                main_menu()
            )

            return

        product = products[
            product_id
        ]

        send_telegram(
            f"🔍 Перевіряю:\n"
            f"{product['name']}..."
        )

        try:

            status, reason = await check_product(
                page,
                product
            )

        except Exception as error:

            status = "error"
            reason = repr(error)

        if status in (
            "unknown",
            "error"
        ):

            send_telegram(
                f"🟡 {product['name']}\n"
                f"🌐 {get_site_name(product['url'])}\n\n"
                f"Не вдалося впевнено визначити.\n"
                f"Причина: {reason}",
                product_keyboard(
                    product_id,
                    product
                )
            )

            return

        product["status"] = status

        save_products(
            products
        )

        send_telegram(
            f"{product_message(product)}\n\n"
            f"{reason}",
            product_keyboard(
                product_id,
                product
            )
        )

        return

    # /add

    if text.startswith("/add"):

        parts = text.split(
            maxsplit=1
        )

        if len(parts) != 2:

            send_telegram(
                "Надішліть посилання після /add.\n\n"
                "Або просто надішліть URL.",
                main_menu()
            )

            return

        url = parts[1].strip()

        send_telegram(
            "🔎 Отримала посилання.\n"
            "Відкриваю сторінку та перевіряю..."
        )

        await add_product(
            url,
            products,
            page
        )

        return

    # ПРОСТАЯ ССЫЛКА

    if (
        text.startswith("http://")
        or text.startswith("https://")
    ):

        send_telegram(
            "🔎 Отримала посилання.\n"
            "Відкриваю сторінку та перевіряю..."
        )

        await add_product(
            text,
            products,
            page
        )

        return


# =========================================================
# TELEGRAM LISTENER
# =========================================================

async def telegram_listener(
    products,
    page
):

    offset = 0

    print(
        "Telegram listener запущено."
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

                print(
                    "Telegram getUpdates error:",
                    result
                )

                await asyncio.sleep(5)

                continue

            for update in result.get(
                "result",
                []
            ):

                offset = (
                    update["update_id"] + 1
                )

                # CALLBACK

                callback = update.get(
                    "callback_query"
                )

                if callback:

                    callback_message = callback.get(
                        "message"
                    )

                    if callback_message:

                        callback_chat_id = str(
                            callback_message["chat"]["id"]
                        )

                        if callback_chat_id == CHAT_ID:

                            try:

                                await handle_callback(
                                    callback,
                                    products,
                                    page
                                )

                            except Exception as error:

                                print(
                                    "Callback error:",
                                    repr(error)
                                )

                    continue

                # ОБЫЧНОЕ СООБЩЕНИЕ

                message = update.get(
                    "message"
                )

                if message:

                    print(
                        "Telegram повідомлення:",
                        message.get("text")
                    )

                    try:

                        await handle_message(
                            message,
                            products,
                            page
                        )

                    except Exception as error:

                        print(
                            "Message handler error:",
                            repr(error)
                        )

        except Exception as error:

            print(
                "Telegram listener error:",
                repr(error)
            )

            await asyncio.sleep(5)


# =========================================================
# МОНИТОРИНГ
# =========================================================

async def monitor_products(
    products,
    browser
):

    print(
        "Моніторинг товарів запущено."
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
                "Перевірка:",
                product_id,
                product["name"]
            )

            # -------------------------------------------------
            # НОВАЯ ОТДЕЛЬНАЯ PAGE
            # -------------------------------------------------

            page = None

            try:

                page = await browser.new_page()

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

                # -------------------------------------------------
                # UNKNOWN / ERROR
                # -------------------------------------------------

                if status in (
                    "unknown",
                    "error"
                ):

                    print(
                        "Стан не змінюємо."
                    )

                    continue

                previous_status = product.get(
                    "status"
                )

                # -------------------------------------------------
                # OUT → IN
                # -------------------------------------------------

                if (
                    previous_status == "out"
                    and status == "in"
                ):

                    send_telegram(
                        f"🟢 "
                        f"{product['name']} "
                        f"З'ЯВИЛАСЯ У ПРОДАЖУ!\n"
                        f"🌐 {get_site_name(product['url'])}\n\n"
                        f"{reason}",
                        product_keyboard(
                            product_id,
                            product
                        )
                    )

                    product["status"] = "in"

                # -------------------------------------------------
                # IN → OUT
                # -------------------------------------------------

                elif (
                    previous_status == "in"
                    and status == "out"
                ):

                    send_telegram(
                        f"🔴 "
                        f"{product['name']} "
                        f"ЗАКІНЧИЛАСЯ!\n"
                        f"🌐 {get_site_name(product['url'])}\n\n"
                        f"{reason}",
                        product_keyboard(
                            product_id,
                            product
                        )
                    )

                    product["status"] = "out"

                # -------------------------------------------------
                # UNKNOWN INITIAL
                # -------------------------------------------------

                elif previous_status is None:

                    product["status"] = status

                    print(
                        "Початковий стан:",
                        status
                    )

                else:

                    print(
                        "Стан не змінився."
                    )

            except Exception as error:

                print(
                    "Помилка моніторингу:",
                    repr(error)
                )

            finally:

                if page:

                    try:
                        await page.close()
                    except Exception:
                        pass

        save_products(
            products
        )

        print()
        print(
            f"Наступна перевірка через "
            f"{CHECK_INTERVAL} секунд."
        )

        print(
            "================================"
        )

        await asyncio.sleep(
            CHECK_INTERVAL
        )


# =========================================================
# MAIN
# =========================================================

async def main():

    print(
        "================================"
    )

    print(
        "🌸 PEONY MONITOR BOT"
    )

    print(
        "БОТ ЗАПУЩЕНО"
    )

    print(
        "================================"
    )

    products = load_products()

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
            ]
        )

        telegram_page = None

        try:

            telegram_page = await browser.new_page()

            await asyncio.gather(
                monitor_products(
                    products,
                    browser
                ),
                telegram_listener(
                    products,
                    telegram_page
                )
            )

        except Exception as error:

            print(
                "MAIN ERROR:",
                repr(error)
            )

        finally:

            try:

                if telegram_page:
                    await telegram_page.close()

            except Exception:
                pass

            try:
                await browser.close()
            except Exception:
                pass


asyncio.run(main())

