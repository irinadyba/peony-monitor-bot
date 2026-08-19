import os
import asyncio
import json
import re
import requests

from playwright.async_api import async_playwright


# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "450401868"

DATA_FILE = "products.json"
CHECK_INTERVAL = 60


# =========================================================
# РОБОТА З ТОВАРАМИ
# =========================================================

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

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            products = json.load(f)

            # Исправляем возможные Markdown-ссылки,
            # если они случайно попали в старый products.json.
            for product in products.values():

                url = product.get("url", "")

                if url.startswith("[") and "](" in url:

                    match = re.search(
                        r"\]\((https?://[^)]+)\)",
                        url
                    )

                    if match:

                        product["url"] = match.group(1)

            return products

    except Exception as error:

        print(
            "Ошибка загрузки products.json:",
            repr(error)
        )

        return {}


def save_products(products):

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            products,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# TELEGRAM
# =========================================================

def telegram_request(
    method,
    data=None,
    json_data=None
):

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/{method}"
    )

    response = requests.post(
        url,
        data=data or {},
        json=json_data,
        timeout=30
    )

    return response.json()


def send_telegram(
    message,
    reply_markup=None
):

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
        data=data
    )

    print(
        "Telegram:",
        result
    )

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
        data=data
    )

    print(
        "Telegram edit:",
        result
    )

    return result


def answer_callback(callback_id):

    telegram_request(
        "answerCallbackQuery",
        data={
            "callback_query_id": callback_id
        }
    )


# =========================================================
# КЛАВІАТУРА — ГОЛОВНЕ МЕНЮ
# =========================================================

def main_menu():

    return {
        "inline_keyboard": [

            [
                {
                    "text": "📋 Мої півонії",
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


# =========================================================
# КНОПКИ ПІД КОЖНОЮ ПІВОНІЄЮ
# =========================================================

def product_keyboard(
    product_id,
    product
):

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
            ]

        ]
    }


# =========================================================
# ПІДТВЕРДЖЕННЯ ВИДАЛЕННЯ
# =========================================================

def delete_confirmation_keyboard(
    product_id
):

    return {
        "inline_keyboard": [

            [
                {
                    "text": "⚠️ Так, видалити",
                    "callback_data": (
                        f"remove_confirm:{product_id}"
                    )
                },
                {
                    "text": "❌ Ні",
                    "callback_data": (
                        f"remove_cancel:{product_id}"
                    )
                }
            ]

        ]
    }


# =========================================================
# ВИБІР ПІВОНІЇ ДЛЯ ПЕРЕВІРКИ
# =========================================================

def choose_product_keyboard(
    products
):

    rows = []

    for product_id, product in products.items():

        status = product.get(
            "status"
        )

        icon = status_icon(
            status
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
                "text": "⬅️ Назад",
                "callback_data": "menu"
            }
        ]
    )

    return {
        "inline_keyboard": rows
    }


# =========================================================
# СТАТУС
# =========================================================

def status_icon(
    status
):

    if status == "in":
        return "🟢"

    if status == "out":
        return "🔴"

    return "🟡"


def status_text(
    status
):

    if status == "in":
        return "В НАЯВНОСТІ"

    if status == "out":
        return "НЕМАЄ В НАЯВНОСТІ"

    return "НЕ ВДАЛОСЯ ВИЗНАЧИТИ"


# =========================================================
# НАЗВА ТОВАРУ
# =========================================================

async def get_product_name(
    page
):

    try:

        title = await page.title()

        if title:

            title = title.strip()

            # Pivoines Rivière
            title = re.sub(
                r"\s*[-|–]\s*Pivoines Rivière.*$",
                "",
                title,
                flags=re.IGNORECASE
            )

            # Убираем типичные хвосты WooCommerce.
            title = re.sub(
                r"\s*\|\s*Graefswinning.*$",
                "",
                title,
                flags=re.IGNORECASE
            )

            title = re.sub(
                r"\s*[-|–]\s*Paeonia Miely.*$",
                "",
                title,
                flags=re.IGNORECASE
            )

            return title.strip()

    except Exception:

        pass

    return "Невідомий товар"


# =========================================================
# ОСНОВНИЙ БЛОК ТОВАРУ GRAEFSWINNING
# =========================================================

async def get_main_product_area(
    page
):

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

            locator = page.locator(
                selector
            )

            count = await locator.count()

            if count == 0:
                continue

            for i in range(count):

                candidate = locator.nth(i)

                try:

                    if not await candidate.is_visible():
                        continue

                    text = await candidate.inner_text()

                    if (
                        text
                        and
                        len(text.strip()) > 20
                    ):

                        return candidate

                except Exception:

                    continue

        except Exception:

            continue

    return None


# =========================================================
# GRAEFSWINNING
# =========================================================

async def check_graefswinning(
    page
):

    product_area = await get_main_product_area(
        page
    )

    if product_area is None:

        return (
            "unknown",
            "Не знайдено основний блок товару"
        )

    try:

        product_text = await product_area.inner_text()

        product_text_lower = (
            product_text.lower()
        )

        # =================================================
        # НЕМАЄ В НАЯВНОСТІ
        # =================================================

        unavailable_phrases = [

            "this variety is not available",
            "this product is not available",
            "this item is not available",

        ]

        for phrase in unavailable_phrases:

            if phrase in product_text_lower:

                return (
                    "out",
                    phrase
                )

        # =================================================
        # Є В НАЯВНОСТІ
        # =================================================

        available_phrases = [

            "order now for the best selection",
            "order now",
            "add to cart",
            "add to basket",
            "in stock",
            "available",

        ]

        for phrase in available_phrases:

            if phrase in product_text_lower:

                return (
                    "in",
                    phrase
                )

        # =================================================
        # ДОДАТКОВА ПЕРЕВІРКА КНОПОК
        # =================================================

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

                if not element_text:
                    continue

                if any(
                    word in element_text
                    for word in [
                        "order now",
                        "add to cart",
                        "add to basket",
                        "order"
                    ]
                ):

                    if await element.is_enabled():

                        return (
                            "in",
                            element_text
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
# ПЕРЕВІРКА ТОВАРУ
# =========================================================

async def check_product(
    page,
    product
):

    url = product["url"]

    try:

        print(
            "Відкриваю:",
            url
        )

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(
            3000
        )

        text = await page.locator(
            "body"
        ).inner_text()

        text_lower = text.lower()

        # =================================================
        # ЗАХИСТ САЙТУ
        # =================================================

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

        # =================================================
        # PIVOINES RIVIÈRE
        # =================================================

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

                    if (
                        "ajouter au panier"
                        in element_text
                    ):

                        if await element.is_enabled():

                            return (
                                "in",
                                "Ajouter au panier"
                            )

                except Exception:

                    continue

            return (
                "out",
                "Кнопка покупки недоступна"
            )

        # =================================================
        # PAEONIA MIELY
        # =================================================

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
                "Товар недоступний"
            )

        # =================================================
        # GRAEFSWINNING
        # =================================================

        if "graefswinning.be" in url.lower():

            return await check_graefswinning(
                page
            )

        # =================================================
        # УНІВЕРСАЛЬНИЙ АЛГОРИТМ
        # =================================================

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

        count = await buttons.count()

        for i in range(count):

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
            "Не вдалося впевнено визначити"
        )

    except Exception as error:

        print(
            "Помилка перевірки:",
            repr(error)
        )

        return (
            "error",
            repr(error)
        )


# =========================================================
# ПОКАЗ СПИСКУ
# =========================================================

def send_product_list(
    products
):

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

        status = product.get(
            "status"
        )

        icon = status_icon(
            status
        )

        message = (
            f"{icon} {product['name']}\n\n"
            f"Статус: {status_text(status)}"
        )

        send_telegram(
            message,
            product_keyboard(
                product_id,
                product
            )
        )


# =========================================================
# ДОДАВАННЯ ТОВАРУ
# =========================================================

async def add_product(
    url,
    products,
    page
):

    # Чистимо URL від випадкової Markdown-обгортки.
    if url.startswith("[") and "](" in url:

        match = re.search(
            r"\]\((https?://[^)]+)\)",
            url
        )

        if match:
            url = match.group(1)

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

            f"🟡 {name}\n\n"
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

        str(
            max(numbers) + 1
        )
        if numbers
        else "1"

    )

    products[product_id] = {

        "name": name,
        "url": url,
        "status": status,

    }

    save_products(
        products
    )

    icon = status_icon(
        status
    )

    state = status_text(
        status
    )

    product = products[
        product_id
    ]

    send_telegram(

        f"{icon} Додано!\n\n"
        f"№ {product_id}\n"
        f"{name}\n\n"
        f"{state}\n"
        f"{reason}",

        product_keyboard(
            product_id,
            product
        )

    )


# =========================================================
# CALLBACK-КНОПКИ
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
    # ГОЛОВНЕ МЕНЮ
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
    # ДОДАВАННЯ
    # =====================================================

    if data == "add_help":

        send_telegram(

            "➕ Додати півонію\n\n"
            "Просто надішліть мені посилання "
            "на сторінку півонії.\n\n"
            "Я відкрию сторінку, перевірю наявність "
            "і додам її до відстеження.",

            main_menu()

        )

        return

    # =====================================================
    # ВИБІР ПІВОНІЇ
    # =====================================================

    if data == "check_choose":

        if not products:

            send_telegram(
                "🌸 Список порожній.",
                main_menu()
            )

            return

        send_telegram(

            "🔍 Оберіть півонію для перевірки:",

            choose_product_keyboard(
                products
            )

        )

        return

    # =====================================================
    # ПЕРЕВІРИТИ ВСІ
    # =====================================================

    if data == "check_all":

        send_telegram(
            "🔄 Перевіряю всі півонії..."
        )

        for product_id, product in list(
            products.items()
        ):

            status, reason = await check_product(
                page,
                product
            )

            if status in (
                "unknown",
                "error"
            ):

                continue

            product["status"] = status

        save_products(
            products
        )

        send_telegram(

            "✅ Перевірку всіх півоній завершено.",

            main_menu()

        )

        return

    # =====================================================
    # ПЕРЕВІРИТИ ОДНУ ПІВОНІЮ
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

        status, reason = await check_product(
            page,
            product
        )

        if status in (
            "unknown",
            "error"
        ):

            send_telegram(

                f"🟡 {product['name']}\n\n"
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

            f"{status_icon(status)} "
            f"{product['name']}\n\n"
            f"{status_text(status)}\n"
            f"{reason}",

            product_keyboard(
                product_id,
                product
            )

        )

        return

    # =====================================================
    # ЗАПИТ НА ВИДАЛЕННЯ
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

        # Вместо отдельного сообщения делаем
        # компактное подтверждение.
        if message_id:

            edit_telegram_message(

                message_id,

                f"🗑 Видалити\n\n"
                f"{product['name']}\n\n"
                f"Ви впевнені?",

                delete_confirmation_keyboard(
                    product_id
                )

            )

        else:

            send_telegram(

                f"🗑 Видалити\n\n"
                f"{product['name']}\n\n"
                f"Ви впевнені?",

                delete_confirmation_keyboard(
                    product_id
                )

            )

        return

    # =====================================================
    # ПІДТВЕРДЖЕННЯ ВИДАЛЕННЯ
    # =====================================================

    if data.startswith(
        "remove_confirm:"
    ):

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

        if message_id:

            edit_telegram_message(

                message_id,

                f"🗑 {removed['name']}\n\n"
                f"Видалено з відстеження.",

                main_menu()

            )

        else:

            send_telegram(
                f"🗑 {removed['name']}\n\n"
                f"Видалено з відстеження.",
                main_menu()
            )

        return

    # =====================================================
    # СКАСУВАННЯ ВИДАЛЕННЯ
    # =====================================================

    if data.startswith(
        "remove_cancel:"
    ):

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

        if message_id:

            edit_telegram_message(

                message_id,

                f"{status_icon(product.get('status'))} "
                f"{product['name']}\n\n"
                f"Статус: "
                f"{status_text(product.get('status'))}",

                product_keyboard(
                    product_id,
                    product
                )

            )

        return


# =========================================================
# ЗВИЧАЙНІ TELEGRAM-ПОВІДОМЛЕННЯ
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

    # =====================================================
    # START
    # =====================================================

    if text == "/start":

        send_telegram(

            "🌸 PEONY MONITOR\n\n"
            "Відстежую наявність півоній "
            "і повідомляю про зміни.\n\n"
            "Оберіть дію:",

            main_menu()

        )

        return

    # =====================================================
    # LIST
    # =====================================================

    if text == "/list":

        send_product_list(
            products
        )

        return

    # =====================================================
    # REMOVE
    # =====================================================

    if text.startswith(
        "/remove"
    ):

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

            f"🗑 Видалити\n\n"
            f"{product['name']}\n\n"
            f"Ви впевнені?",

            delete_confirmation_keyboard(
                product_id
            )

        )

        return

    # =====================================================
    # CHECK
    # =====================================================

    if text.startswith(
        "/check"
    ):

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

        status, reason = await check_product(
            page,
            product
        )

        if status in (
            "unknown",
            "error"
        ):

            send_telegram(

                f"🟡 {product['name']}\n\n"
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

            f"{status_icon(status)} "
            f"{product['name']}\n\n"
            f"{status_text(status)}\n"
            f"{reason}",

            product_keyboard(
                product_id,
                product
            )

        )

        return

    # =====================================================
    # ADD
    # =====================================================

    if text.startswith(
        "/add"
    ):

        parts = text.split(
            maxsplit=1
        )

        if len(parts) != 2:

            send_telegram(

                "Надішліть посилання після /add.\n\n"
                "Або просто надішліть URL "
                "без команди.",

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

    # =====================================================
    # ПРОСТА ССИЛКА
    # =====================================================

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

            if not result.get(
                "ok"
            ):

                await asyncio.sleep(
                    5
                )

                continue

            for update in result.get(
                "result",
                []
            ):

                offset = (
                    update["update_id"] + 1
                )

                # =================================================
                # CALLBACK-КНОПКА
                # =================================================

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

                            await handle_callback(

                                callback,
                                products,
                                page

                            )

                    continue

                # =================================================
                # ОБЫЧНОЕ СООБЩЕНИЕ
                # =================================================

                message = update.get(
                    "message"
                )

                if message:

                    print(
                        "Telegram повідомлення:",
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

            await asyncio.sleep(
                5
            )


# =========================================================
# МОНІТОРИНГ
# =========================================================

async def monitor_products(
    products,
    page
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

            # =================================================
            # UNKNOWN / ERROR
            # =================================================

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

            # =================================================
            # ПОЧАТКОВИЙ СТАН
            # =================================================

            if previous_status is None:

                product["status"] = status

                print(
                    "Початковий стан:",
                    status
                )

            # =================================================
            # OUT -> IN
            # =================================================

            elif (
                previous_status == "out"
                and status == "in"
            ):

                send_telegram(

                    f"🟢 "
                    f"{product['name']}\n\n"
                    f"З'ЯВИЛАСЯ У ПРОДАЖУ!\n"
                    f"{reason}",

                    product_keyboard(
                        product_id,
                        product
                    )

                )

                product["status"] = "in"

            # =================================================
            # IN -> OUT
            # =================================================

            elif (
                previous_status == "in"
                and status == "out"
            ):

                send_telegram(

                    f"🔴 "
                    f"{product['name']}\n\n"
                    f"ЗАКІНЧИЛАСЯ!\n"
                    f"{reason}",

                    product_keyboard(
                        product_id,
                        product
                    )

                )

                product["status"] = "out"

            # =================================================
            # БЕЗ ЗМІН
            # =================================================

            else:

                print(
                    "Стан не змінився."
                )

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
