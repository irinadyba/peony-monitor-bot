import os
import asyncio
import json
import re
import requests

from playwright.async_api import async_playwright


# =========================================================
# НАСТРОЙКИ
# =========================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "450401868"

DATA_FILE = "products.json"

CHECK_INTERVAL = 60

PAGE_TIMEOUT = 60000

PAGE_WAIT = 3000


# =========================================================
# НАЧАЛЬНЫЕ ТОВАРЫ
# =========================================================

DEFAULT_PRODUCTS = {
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


# =========================================================
# PRODUCTS.JSON
# =========================================================

def load_products():

    if not os.path.exists(DATA_FILE):

        print("products.json не найден.")

        products = dict(DEFAULT_PRODUCTS)

        save_products(products)

        print("products.json создан автоматически.")

        return products

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            products = json.load(f)

        if not isinstance(products, dict):

            raise ValueError(
                "products.json должен содержать объект"
            )

        print(
            f"Загружено товаров: {len(products)}"
        )

        return products

    except Exception as error:

        print(
            "Ошибка чтения products.json:",
            repr(error)
        )

        # ВАЖНО:
        # Не уничтожаем файл автоматически.
        # Если он повреждён, запускаем начальный список.

        products = dict(DEFAULT_PRODUCTS)

        save_products(products)

        return products


def save_products(products):

    temporary_file = DATA_FILE + ".tmp"

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            products,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temporary_file,
        DATA_FILE
    )


# =========================================================
# TELEGRAM API
# =========================================================

def telegram_request(
    method,
    data=None
):

    url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/{method}"
    )

    response = requests.post(
        url,
        data=data or {},
        timeout=35
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

    try:

        result = telegram_request(
            "sendMessage",
            data
        )

        print(
            "Telegram:",
            result
        )

        return result

    except Exception as error:

        print(
            "Telegram send error:",
            repr(error)
        )

        return None


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

    try:

        result = telegram_request(
            "editMessageText",
            data
        )

        print(
            "Telegram edit:",
            result
        )

        return result

    except Exception as error:

        print(
            "Telegram edit error:",
            repr(error)
        )

        return None


def answer_callback(
    callback_id
):

    try:

        telegram_request(
            "answerCallbackQuery",
            {
                "callback_query_id": callback_id
            }
        )

    except Exception as error:

        print(
            "Callback answer error:",
            repr(error)
        )


# =========================================================
# НИЖНЯ КНОПКА TELEGRAM
# =========================================================

def bottom_menu_keyboard():

    return {
        "keyboard": [
            [
                {
                    "text": "🌸 Головне меню"
                }
            ]
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


# =========================================================
# ГОЛОВНЕ МЕНЮ
# =========================================================

def main_menu():

    return {
        "inline_keyboard": [

            [
                {
                    "text": "📋 Мої півонії",
                    "callback_data": "list"
                }
            ],

            [
                {
                    "text": "➕ Додати півонію",
                    "callback_data": "add_help"
                }
            ],

            [
                {
                    "text": "🔄 Перевірити всі",
                    "callback_data": "check_all"
                }
            ],

            [
                {
                    "text": "🔍 Перевірити півонію",
                    "callback_data": "check_choose"
                }
            ],

        ]
    }


def show_main_menu():

    send_telegram(
        "🌸 PEONY MONITOR\n\n"
        "Оберіть потрібну дію:",
        main_menu()
    )


# =========================================================
# НАЗВА САЙТУ З URL
# =========================================================

def get_site_name(url):

    match = re.search(
        r"https?://(?:www\.)?([^./]+)",
        url,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

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
# КНОПКИ ТОВАРУ
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
                    "callback_data":
                        f"check:{product_id}"
                },

                {
                    "text": "🗑 Видалити",
                    "callback_data":
                        f"remove:{product_id}"
                }
            ]

        ]
    }


# =========================================================
# ПІДТВЕРЖДЕННЯ ВИДАЛЕННЯ
# =========================================================

def delete_confirmation_keyboard(
    product_id
):

    return {
        "inline_keyboard": [

            [
                {
                    "text": "✅ Видалити",
                    "callback_data":
                        f"remove_confirm:{product_id}"
                },

                {
                    "text": "❌ Скасувати",
                    "callback_data":
                        f"remove_cancel:{product_id}"
                }
            ]

        ]
    }


# =========================================================
# ВИБІР ТОВАРУ
# =========================================================

def choose_product_keyboard(
    products
):

    rows = []

    for product_id, product in products.items():

        icon = status_icon(
            product.get("status")
        )

        rows.append(
            [
                {
                    "text":
                        f"{icon} {product['name']}",
                    "callback_data":
                        f"check:{product_id}"
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
# НАЗВА ТОВАРУ
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

            return title

    except Exception:

        pass

    return "Невідомий товар"


# =========================================================
# BROWSER MANAGER
# =========================================================

class BrowserManager:

    def __init__(
        self,
        playwright
    ):

        self.playwright = playwright

        self.browser = None

        self.lock = asyncio.Lock()


    async def ensure_browser(self):

        async with self.lock:

            if self.browser is not None:

                try:

                    if self.browser.is_connected():

                        return self.browser

                except Exception:

                    pass

            print(
                "Запускаю Chromium..."
            )

            try:

                self.browser = await (
                    self.playwright.chromium.launch(
                        headless=True,
                        args=[
                            "--disable-dev-shm-usage",
                            "--no-sandbox",
                            "--disable-gpu",
                            "--disable-software-rasterizer",
                        ]
                    )
                )

                print(
                    "Chromium запущен."
                )

                return self.browser

            except Exception as error:

                print(
                    "Не удалось запустить Chromium:",
                    repr(error)
                )

                self.browser = None

                raise


    async def new_page(self):

        browser = await self.ensure_browser()

        try:

            page = await browser.new_page()

            return page

        except Exception as error:

            print(
                "Не удалось создать страницу:",
                repr(error)
            )

            await self.restart()

            browser = await self.ensure_browser()

            return await browser.new_page()


    async def restart(self):

        async with self.lock:

            print(
                "Перезапускаю Chromium..."
            )

            if self.browser is not None:

                try:

                    await self.browser.close()

                except Exception:

                    pass

            self.browser = None


    async def close(self):

        async with self.lock:

            if self.browser is not None:

                try:

                    await self.browser.close()

                except Exception:

                    pass

                self.browser = None


# =========================================================
# ОСНОВНОЙ БЛОК GRAEFSWINNING
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

        product_text = await (
            product_area.inner_text()
        )

        text = product_text.lower()

        # НЕМАЄ В НАЯВНОСТІ

        unavailable_phrases = [

            "this variety is not available",

            "this product is not available",

            "this variety is unavailable",

        ]

        for phrase in unavailable_phrases:

            if phrase in text:

                return (
                    "out",
                    phrase
                )

        # Є В НАЯВНОСТІ

        if (
            "order now for the best selection"
            in text
        ):

            return (
                "in",
                "Order now for the best selection"
            )

        # Add to cart

        buttons = product_area.locator(
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

                if "add to cart" in element_text:

                    if await element.is_enabled():

                        return (
                            "in",
                            "Add to cart"
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
# ПРОВЕРКА PIVOINES RIVIÈRE
# =========================================================

async def check_pivoines_riviere(
    page
):

    text = await page.locator(
        "body"
    ).inner_text()

    text_lower = text.lower()

    out_phrases = [

        "rupture de stock",

        "épuisée pour cette année",

        "notify me when available",

    ]

    for phrase in out_phrases:

        if phrase in text_lower:

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

            if "ajouter au panier" in element_text:

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


# =========================================================
# ПРОВЕРКА PAEONIA MIELY
# =========================================================

async def check_paeonia_miely(
    page
):

    text = await page.locator(
        "body"
    ).inner_text()

    text_lower = text.lower()

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


# =========================================================
# УНИВЕРСАЛЬНАЯ ПРОВЕРКА
# =========================================================

async def check_product(
    browser_manager,
    product
):

    url = product["url"]

    page = None

    try:

        print(
            "Відкриваю:",
            url
        )

        page = await browser_manager.new_page()

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT
        )

        await page.wait_for_timeout(
            PAGE_WAIT
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

            return await check_pivoines_riviere(
                page
            )

        # =================================================
        # PAEONIA MIELY
        # =================================================

        if "paeoniamiely.com" in url.lower():

            return await check_paeonia_miely(
                page
            )

        # =================================================
        # GRAEFSWINNING
        # =================================================

        if "graefswinning.be" in url.lower():

            return await check_graefswinning(
                page
            )

        # =================================================
        # УНИВЕРСАЛЬНЫЙ АЛГОРИТМ
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

        return (
            "unknown",
            "Не вдалося впевнено визначити"
        )

    except Exception as error:

        error_text = repr(error)

        print(
            "Помилка перевірки:",
            error_text
        )

        # =================================================
        # КРИТИЧНА ПОМИЛКА PLAYWRIGHT
        # =================================================

        if (
            "TargetClosedError"
            in error_text
            or
            "Page crashed"
            in error_text
            or
            "Browser has been closed"
            in error_text
        ):

            print(
                "Виявлено падіння Chromium."
            )

            try:

                await browser_manager.restart()

            except Exception:

                pass

        return (
            "error",
            error_text
        )

    finally:

        if page is not None:

            try:

                await page.close()

            except Exception:

                pass


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

        icon = status_icon(
            product.get("status")
        )

        site = get_site_name(
            product["url"]
        )

        message = (
            f"{icon} {product['name']}\n"
            f"🌐 {site}\n\n"
            f"Статус: "
            f"{status_text(product.get('status'))}"
        )

        send_telegram(
            message,
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
    browser_manager
):

    temporary_product = {

        "name": "Новий товар",

        "url": url,

        "status": None,

    }

    status, reason = await check_product(
        browser_manager,
        temporary_product
    )

    # Для названия нужна отдельная страница

    page = None

    try:

        page = await browser_manager.new_page()

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT
        )

        await page.wait_for_timeout(
            1500
        )

        name = await get_product_name(
            page
        )

    except Exception:

        name = "Новий товар"

    finally:

        if page is not None:

            try:

                await page.close()

            except Exception:

                pass

    if status in (
        "unknown",
        "error"
    ):

        site = get_site_name(
            url
        )

        send_telegram(

            f"🟡 {name}\n"
            f"🌐 {site}\n\n"
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

    site = get_site_name(
        url
    )

    product = products[
        product_id
    ]

    send_telegram(

        f"{icon} Додано!\n\n"
        f"№ {product_id}\n"
        f"{name}\n"
        f"🌐 {site}\n\n"
        f"{status_text(status)}\n"
        f"{reason}",

        product_keyboard(
            product_id,
            product
        )
    )


# =========================================================
# CALLBACK КНОПКИ
# =========================================================

async def handle_callback(
    callback,
    products,
    browser_manager
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
    # МЕНЮ
    # =====================================================

    if data == "menu":

        if message_id:

            edit_telegram_message(

                message_id,

                "🌸 PEONY MONITOR\n\n"
                "Оберіть дію:",

                main_menu()

            )

        else:

            show_main_menu()

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
            "Просто надішліть мені URL "
            "сторінки півонії.\n\n"
            "Я відкрию сторінку, визначу "
            "наявність і додам її до відстеження.",

            main_menu()
        )

        return

    # =====================================================
    # ВЫБОР ПИОНА
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

            choose_product_keyboard(
                products
            )
        )

        return

    # =====================================================
    # ПРОВЕРИТЬ ВСЕ
    # =====================================================

    if data == "check_all":

        send_telegram(
            "🔄 Перевіряю всі півонії..."
        )

        for product_id, product in list(
            products.items()
        ):

            try:

                status, reason = await check_product(
                    browser_manager,
                    product
                )

                if status in (
                    "unknown",
                    "error"
                ):

                    continue

                previous_status = product.get(
                    "status"
                )

                product["status"] = status

                if (
                    previous_status == "out"
                    and status == "in"
                ):

                    send_telegram(

                        f"🟢 {product['name']}\n"
                        f"🌐 {get_site_name(product['url'])}\n\n"
                        f"З'ЯВИЛАСЯ У ПРОДАЖУ!\n\n"
                        f"{reason}",

                        product_keyboard(
                            product_id,
                            product
                        )
                    )

            except Exception as error:

                print(
                    "Ошибка callback check_all:",
                    repr(error)
                )

                continue

        save_products(
            products
        )

        send_telegram(
            "✅ Перевірку завершено.",
            main_menu()
        )

        return

    # =====================================================
    # ПРОВЕРИТЬ ОДИН
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
            browser_manager,
            product
        )

        if status in (
            "unknown",
            "error"
        ):

            send_telegram(

                f"🟡 {product['name']}\n"
                f"🌐 {get_site_name(product['url'])}\n\n"
                f"НЕ ВДАЛОСЯ ВИЗНАЧИТИ\n\n"
                f"{reason}",

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
            f"{product['name']}\n"
            f"🌐 {get_site_name(product['url'])}\n\n"
            f"{status_text(status)}\n"
            f"{reason}",

            product_keyboard(
                product_id,
                product
            )
        )

        return

    # =====================================================
    # ЗАПРОС УДАЛЕНИЯ
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
    # ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ
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

        send_telegram(

            f"🗑 {removed['name']}\n"
            f"Видалено з відстеження.",

            main_menu()
        )

        return

    # =====================================================
    # ОТМЕНА
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

        send_telegram(

            f"❌ Видалення скасовано.\n\n"
            f"{product['name']}",

            product_keyboard(
                product_id,
                product
            )
        )

        return


# =========================================================
# ОБЫЧНЫЕ TELEGRAM СООБЩЕНИЯ
# =========================================================

async def handle_message(
    message,
    products,
    browser_manager
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
    # ГЛАВНОЕ МЕНЮ
    # =====================================================

    if text in (
        "/start",
        "🌸 Головне меню"
    ):

        send_telegram(

            "🌸 PEONY MONITOR\n\n"
            "Оберіть потрібну дію:",

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
                "Напишіть номер.\n"
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
            browser_manager,
            product
        )

        if status not in (
            "unknown",
            "error"
        ):

            product["status"] = status

            save_products(
                products
            )

        send_telegram(

            f"{status_icon(status)} "
            f"{product['name']}\n"
            f"🌐 {get_site_name(product['url'])}\n\n"
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

                "Надішліть URL після /add.\n\n"
                "Або просто надішліть мені URL "
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
            browser_manager
        )

        return

    # =====================================================
    # ПРОСТОЙ URL
    # =====================================================

    if (
        text.startswith("http://")
        or
        text.startswith("https://")
    ):

        send_telegram(
            "🔎 Отримала посилання.\n"
            "Відкриваю сторінку та перевіряю..."
        )

        await add_product(
            text,
            products,
            browser_manager
        )

        return


# =========================================================
# TELEGRAM LISTENER
# =========================================================

async def telegram_listener(
    products,
    browser_manager
):

    offset = 0

    print(
        "Telegram listener запущено."
    )

    # Показываем меню при запуске

    send_telegram(

        "🌸 PEONY MONITOR\n\n"
        "Бот запущено.\n"
        "Оберіть потрібну дію:",

        main_menu()
    )

    while True:

        try:

            result = await asyncio.to_thread(

                telegram_request,

                "getUpdates",

                {
                    "offset": offset,

                    "timeout": 25,

                    "allowed_updates":
                        json.dumps([
                            "message",
                            "callback_query"
                        ])
                }
            )

            if not result.get("ok"):

                print(
                    "Telegram API error:",
                    result
                )

                await asyncio.sleep(
                    5
                )

                continue

            updates = result.get(
                "result",
                []
            )

            for update in updates:

                offset = (
                    update["update_id"] + 1
                )

                # =========================================
                # CALLBACK
                # =========================================

                callback = update.get(
                    "callback_query"
                )

                if callback:

                    try:

                        callback_message = (
                            callback.get("message")
                        )

                        if callback_message:

                            callback_chat_id = str(
                                callback_message[
                                    "chat"
                                ]["id"]
                            )

                            if (
                                callback_chat_id
                                == CHAT_ID
                            ):

                                await handle_callback(
                                    callback,
                                    products,
                                    browser_manager
                                )

                    except Exception as error:

                        print(
                            "Callback error:",
                            repr(error)
                        )

                    continue

                # =========================================
                # MESSAGE
                # =========================================

                message = update.get(
                    "message"
                )

                if message:

                    try:

                        print(
                            "Telegram:",
                            message.get("text")
                        )

                        await handle_message(
                            message,
                            products,
                            browser_manager
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

            # ВАЖНО:
            # Telegram не прекращает работу
            # после ошибки.

            await asyncio.sleep(
                5
            )


# =========================================================
# МОНИТОРИНГ
# =========================================================

async def monitor_products(
    products,
    browser_manager
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

            try:

                status, reason = await check_product(
                    browser_manager,
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

            except Exception as error:

                print(
                    "Помилка моніторингу:",
                    repr(error)
                )

                continue

            # =============================================
            # UNKNOWN / ERROR
            # =============================================

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

            # =============================================
            # ПЕРВИЧНОЕ СОСТОЯНИЕ
            # =============================================

            if previous_status is None:

                product["status"] = status

                print(
                    "Початковий стан:",
                    status
                )

            # =============================================
            # OUT → IN
            # =============================================

            elif (
                previous_status == "out"
                and
                status == "in"
            ):

                print(
                    "‼️ ТОВАР З'ЯВИВСЯ!"
                )

                send_telegram(

                    f"🟢 {product['name']}\n"
                    f"🌐 {get_site_name(product['url'])}\n\n"
                    f"З'ЯВИЛАСЯ У ПРОДАЖУ!\n\n"
                    f"{reason}",

                    product_keyboard(
                        product_id,
                        product
                    )
                )

                product["status"] = "in"

            # =============================================
            # IN → OUT
            # =============================================

            elif (
                previous_status == "in"
                and
                status == "out"
            ):

                print(
                    "Товар закінчився."
                )

                send_telegram(

                    f"🔴 {product['name']}\n"
                    f"🌐 {get_site_name(product['url'])}\n\n"
                    f"ЗАКІНЧИЛАСЯ!\n\n"
                    f"{reason}",

                    product_keyboard(
                        product_id,
                        product
                    )
                )

                product["status"] = "out"

            else:

                print(
                    "Стан не змінився."
                )

        # Сохраняем после каждого полного цикла

        try:

            save_products(
                products
            )

        except Exception as error:

            print(
                "Ошибка сохранения products.json:",
                repr(error)
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

    # =============================================
    # Загружаем товары
    # =============================================

    products = load_products()

    # =============================================
    # Playwright
    # =============================================

    async with async_playwright() as playwright:

        browser_manager = BrowserManager(
            playwright
        )

        try:

            # =========================================
            # КРИТИЧЕСКИ ВАЖНО:
            #
            # Telegram listener и мониторинг
            # работают как две независимые задачи.
            #
            # Падение Playwright НЕ должно
            # остановить Telegram.
            # =========================================

            await asyncio.gather(

                telegram_listener(
                    products,
                    browser_manager
                ),

                monitor_products(
                    products,
                    browser_manager
                )

            )

        except Exception as error:

            print(
                "Критическая ошибка main:",
                repr(error)
            )

        finally:

            try:

                await browser_manager.close()

            except Exception:

                pass


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
