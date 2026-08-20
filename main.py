import os
import asyncio
import json
import re
import base64
import requests

from playwright.async_api import async_playwright


# =========================================================
# НАСТРОЙКИ
# =========================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = str(os.environ["TELEGRAM_CHAT_ID"])

GITHUB_TOKEN = os.environ["DATA_REPO_TOKEN"]

GITHUB_OWNER = "irinadyba"
GITHUB_REPO = "peony-monitor-data"
GITHUB_BRANCH = "main"

PRODUCTS_FILE = "products.json"
STATE_FILE = "state.json"

CHECK_INTERVAL = 300

PAGE_TIMEOUT = 60000
PAGE_WAIT = 3000

GITHUB_API = "https://api.github.com"


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
# GITHUB
# =========================================================

def github_headers():

    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2026-03-10",
    }


def github_get_file(path):

    url = (
        f"{GITHUB_API}/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    )

    response = requests.get(
        url,
        headers=github_headers(),
        params={"ref": GITHUB_BRANCH},
        timeout=30,
    )

    if response.status_code == 404:
        return None, None

    response.raise_for_status()

    data = response.json()

    content = base64.b64decode(
        data["content"].replace("\n", "")
    ).decode("utf-8")

    return content, data["sha"]


def github_save_file(path, content, sha=None, message="Update data"):

    url = (
        f"{GITHUB_API}/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    )

    encoded = base64.b64encode(
        content.encode("utf-8")
    ).decode("ascii")

    payload = {
        "message": message,
        "content": encoded,
        "branch": GITHUB_BRANCH,
    }

    if sha:
        payload["sha"] = sha

    response = requests.put(
        url,
        headers=github_headers(),
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    print(
        f"GitHub: {path} сохранён."
    )


def load_products():

    content, sha = github_get_file(
        PRODUCTS_FILE
    )

    if content is None:

        print(
            "products.json отсутствует."
        )

        products = dict(DEFAULT_PRODUCTS)

        github_save_file(
            PRODUCTS_FILE,
            json.dumps(
                products,
                ensure_ascii=False,
                indent=2
            ),
            message="Create products.json",
        )

        return products

    try:

        products = json.loads(content)

        if not isinstance(products, dict):

            raise ValueError(
                "products.json должен быть объектом"
            )

        print(
            f"Загружено товаров: {len(products)}"
        )

        return products

    except Exception as error:

        print(
            "Ошибка products.json:",
            repr(error)
        )

        raise


def save_products(products):

    content, sha = github_get_file(
        PRODUCTS_FILE
    )

    github_save_file(
        PRODUCTS_FILE,
        json.dumps(
            products,
            ensure_ascii=False,
            indent=2
        ),
        sha=sha,
        message="Update products.json",
    )


def load_state():

    content, sha = github_get_file(
        STATE_FILE
    )

    if content is None:

        return {
            "telegram_offset": 0
        }

    try:

        state = json.loads(content)

        if not isinstance(state, dict):

            return {
                "telegram_offset": 0
            }

        return state

    except Exception:

        return {
            "telegram_offset": 0
        }


def save_state(state):

    content, sha = github_get_file(
        STATE_FILE
    )

    github_save_file(
        STATE_FILE,
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2
        ),
        sha=sha,
        message="Update bot state",
    )


# =========================================================
# TELEGRAM
# =========================================================

def telegram_request(method, data=None):

    url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/{method}"
    )

    response = requests.post(
        url,
        data=data or {},
        timeout=35,
    )

    response.raise_for_status()

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


def answer_callback(callback_id):

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
# TELEGRAM КЛАВИАТУРЫ
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

    send_telegram(
        "⬇️ Головне меню",
        bottom_menu_keyboard()
    )


# =========================================================
# САЙТ
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
# КНОПКИ
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


def delete_confirmation_keyboard(product_id):

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


def choose_product_keyboard(products):

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
# НАЗВА
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
# BROWSER
# =========================================================

class BrowserManager:

    def __init__(self, playwright):

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


    async def new_page(self):

        browser = await self.ensure_browser()

        try:

            return await browser.new_page()

        except Exception:

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


async def check_graefswinning(page):

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

        if (
            "order now for the best selection"
            in text
        ):

            return (
                "in",
                "Order now for the best selection"
            )

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
# PIVOINES RIVIÈRE
# =========================================================

async def check_pivoines_riviere(page):

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
# PAEONIA MIELY
# =========================================================

async def check_paeonia_miely(page):

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

        if "pivoinesriviere.com" in url.lower():

            return await check_pivoines_riviere(
                page
            )

        if "paeoniamiely.com" in url.lower():

            return await check_paeonia_miely(
                page
            )

        if "graefswinning.be" in url.lower():

            return await check_graefswinning(
                page
            )

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

        if (
            "TargetClosedError" in error_text
            or
            "Page crashed" in error_text
            or
            "Browser has been closed" in error_text
        ):

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

        site = get_site_name(url)

        send_telegram(

            f"🟡 {name}\n"
            f"🌐 {site}\n\n"
            f"Не вдалося впевнено визначити наявність.\n"
            f"Причина: {reason}\n\n"
            f"Товар НЕ додано до відстеження.",

            main_menu()
        )

        return False

    numbers = []

    for key in products:

        try:
            numbers.append(int(key))
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

    icon = status_icon(status)

    site = get_site_name(url)

    product = products[product_id]

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

    return True


# =========================================================
# CALLBACK
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

    answer_callback(
        callback_id
    )

    # -----------------------------------------------------
    # MENU
    # -----------------------------------------------------

    if data == "menu":

        show_main_menu()

        return True

    # -----------------------------------------------------
    # LIST
    # -----------------------------------------------------

    if data == "list":

        send_product_list(products)

        return False

    # -----------------------------------------------------
    # ADD HELP
    # -----------------------------------------------------

    if data == "add_help":

        send_telegram(

            "➕ Додати півонію\n\n"
            "Просто надішліть мені URL "
            "сторінки півонії.\n\n"
            "Я відкрию сторінку, визначу "
            "наявність і додам її до відстеження.",

            main_menu()
        )

        return False

    # -----------------------------------------------------
    # CHOOSE
    # -----------------------------------------------------

    if data == "check_choose":

        if not products:

            send_telegram(
                "Список порожній.",
                main_menu()
            )

            return False

        send_telegram(
            "🔍 Оберіть півонію:",
            choose_product_keyboard(products)
        )

        return False

    # -----------------------------------------------------
    # CHECK ALL
    # -----------------------------------------------------

    if data == "check_all":

        send_telegram(
            "🔄 Перевіряю всі півонії..."
        )

        await check_all_products(
            products,
            browser_manager
        )

        send_telegram(
            "✅ Перевірку завершено.",
            main_menu()
        )

        return True

    # -----------------------------------------------------
    # CHECK ONE
    # -----------------------------------------------------

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

            return False

        product = products[product_id]

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

        return True

    # -----------------------------------------------------
    # REMOVE
    # -----------------------------------------------------

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

            return False

        product = products[product_id]

        send_telegram(

            f"🗑 Видалити\n"
            f"«{product['name']}»\n"
            f"з відстеження?",

            delete_confirmation_keyboard(
                product_id
            )
        )

        return False

    # -----------------------------------------------------
    # REMOVE CONFIRM
    # -----------------------------------------------------

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

            return False

        removed = products.pop(
            product_id
        )

        send_telegram(

            f"🗑 {removed['name']}\n"
            f"Видалено з відстеження.",

            main_menu()
        )

        return True

    # -----------------------------------------------------
    # REMOVE CANCEL
    # -----------------------------------------------------

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

            return False

        product = products[product_id]

        send_telegram(

            f"❌ Видалення скасовано.\n\n"
            f"{product['name']}",

            product_keyboard(
                product_id,
                product
            )
        )

        return False

    return False


# =========================================================
# ОБЫЧНОЕ СООБЩЕНИЕ
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
        return False

    text = message.get(
        "text",
        ""
    ).strip()

    if not text:
        return False

    # -----------------------------------------------------
    # MENU
    # -----------------------------------------------------

    if text in (
        "/start",
        "🌸 Головне меню"
    ):

        show_main_menu()

        return False

    # -----------------------------------------------------
    # LIST
    # -----------------------------------------------------

    if text == "/list":

        send_product_list(products)

        return False

    # -----------------------------------------------------
    # REMOVE
    # -----------------------------------------------------

    if text.startswith("/remove"):

        parts = text.split()

        if len(parts) != 2:

            send_telegram(
                "Напишіть номер.\n"
                "Наприклад: /remove 2",
                main_menu()
            )

            return False

        product_id = parts[1]

        if product_id not in products:

            send_telegram(
                "Такого номера немає.",
                main_menu()
            )

            return False

        product = products[product_id]

        send_telegram(

            f"🗑 Видалити\n"
            f"«{product['name']}»\n"
            f"з відстеження?",

            delete_confirmation_keyboard(
                product_id
            )
        )

        return False

    # -----------------------------------------------------
    # CHECK
    # -----------------------------------------------------

    if text.startswith("/check"):

        parts = text.split()

        if len(parts) != 2:

            send_telegram(
                "Напишіть номер.\n"
                "Наприклад: /check 2",
                main_menu()
            )

            return False

        product_id = parts[1]

        if product_id not in products:

            send_telegram(
                "Такого номера немає.",
                main_menu()
            )

            return False

        product = products[product_id]

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

        return True

    # -----------------------------------------------------
    # ADD
    # -----------------------------------------------------

    if text.startswith("/add"):

        parts = text.split(
            maxsplit=1
        )

        if len(parts) != 2:

            send_telegram(

                "Надішліть URL після /add.\n\n"
                "Або просто надішліть URL "
                "без команди.",

                main_menu()
            )

            return False

        url = parts[1].strip()

        send_telegram(
            "🔎 Отримала посилання.\n"
            "Відкриваю сторінку та перевіряю..."
        )

        added = await add_product(
            url,
            products,
            browser_manager
        )

        return added

    # -----------------------------------------------------
    # URL
    # -----------------------------------------------------

    if (
        text.startswith("http://")
        or
        text.startswith("https://")
    ):

        send_telegram(
            "🔎 Отримала посилання.\n"
            "Відкриваю сторінку та перевіряю..."
        )

        added = await add_product(
            text,
            products,
            browser_manager
        )

        return added

    return False


# =========================================================
# TELEGRAM UPDATES
# =========================================================

async def process_telegram_updates(
    products,
    browser_manager,
    state
):

    offset = int(
        state.get(
            "telegram_offset",
            0
        )
    )

    changed = False

    try:

        result = await asyncio.to_thread(

            telegram_request,

            "getUpdates",

            {
                "offset": offset,

                "timeout": 1,

                "allowed_updates":
                    json.dumps([
                        "message",
                        "callback_query"
                    ])
            }
        )

    except Exception as error:

        print(
            "Telegram getUpdates error:",
            repr(error)
        )

        return changed

    if not result.get("ok"):

        print(
            "Telegram API error:",
            result
        )

        return changed

    updates = result.get(
        "result",
        []
    )

    for update in updates:

        update_id = update["update_id"]

        state["telegram_offset"] = (
            update_id + 1
        )

        callback = update.get(
            "callback_query"
        )

        if callback:

            try:

                callback_message = callback.get(
                    "message"
                )

                if callback_message:

                    callback_chat_id = str(
                        callback_message["chat"]["id"]
                    )

                    if callback_chat_id == CHAT_ID:

                        result_changed = (
                            await handle_callback(
                                callback,
                                products,
                                browser_manager
                            )
                        )

                        if result_changed:
                            changed = True

            except Exception as error:

                print(
                    "Callback error:",
                    repr(error)
                )

            continue

        message = update.get(
            "message"
        )

        if message:

            try:

                result_changed = (
                    await handle_message(
                        message,
                        products,
                        browser_manager
                    )
                )

                if result_changed:
                    changed = True

            except Exception as error:

                print(
                    "Message handler error:",
                    repr(error)
                )

    return changed


# =========================================================
# ПРОВЕРКА ВСЕХ
# =========================================================

async def check_all_products(
    products,
    browser_manager
):

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
                "Ошибка:",
                repr(error)
            )

            continue

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

        if previous_status is None:

            product["status"] = status

            print(
                "Початковий стан:",
                status
            )

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


# =========================================================
# MAIN
# =========================================================

async def main():

    print(
        "================================"
    )

    print(
        "🌸 PEONY MONITOR"
    )

    print(
        "GitHub Actions запуск"
    )

    print(
        "================================"
    )

    products = load_products()

    state = load_state()

    print(
        "Telegram offset:",
        state.get("telegram_offset", 0)
    )

    async with async_playwright() as playwright:

        browser_manager = BrowserManager(
            playwright
        )

        try:

            # =================================================
            # 1. СНАЧАЛА ОБРАБАТЫВАЕМ TELEGRAM
            # =================================================

            telegram_changed = (
                await process_telegram_updates(
                    products,
                    browser_manager,
                    state
                )
            )

            # =================================================
            # 2. ПРОВЕРЯЕМ ВСЕ ТОВАРЫ
            # =================================================

            await check_all_products(
                products,
                browser_manager
            )

            # =================================================
            # 3. СОХРАНЯЕМ ДАННЫЕ
            # =================================================

            if telegram_changed:

                print(
                    "Telegram изменил список товаров."
                )

            save_products(
                products
            )

            save_state(
                state
            )

            print(
                "Все данные сохранены в GitHub."
            )

        finally:

            await browser_manager.close()


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
