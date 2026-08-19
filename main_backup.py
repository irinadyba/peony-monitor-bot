import os
import asyncio
import requests
from playwright.async_api import async_playwright

PRODUCT_NAME = "ALESIA"
PRODUCT_URL = "https://pivoinesriviere.com/produit/alesia/"

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "450401868"


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    print("Telegram:", response.status_code, response.text)


async def check_product(page):
    try:
        await page.goto(
            PRODUCT_URL,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        await page.wait_for_timeout(3000)

        text = await page.locator("body").inner_text()
        text_lower = text.lower()

        # Явные признаки отсутствия товара
        out_of_stock_phrases = [
            "rupture de stock",
            "notify me when available",
            "épuisée pour cette année",
        ]

        for phrase in out_of_stock_phrases:
            if phrase.lower() in text_lower:
                return "out", phrase

        # Проверяем кнопку добавления в корзину
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

    except Exception as error:
        return "error", repr(error)


async def main():
    print("БОТ ЗАПУЩЕН")
    print("Мониторинг:", PRODUCT_NAME)
    print("Интервал: 60 секунд")

    # Первое состояние пока не отправляем.
    last_status = None

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        try:
            while True:

                print()
                print("================================")
                print("ПРОВЕРКА:", PRODUCT_NAME)
                print("URL:", PRODUCT_URL)

                status, reason = await check_product(page)

                print("STATUS:", status)
                print("REASON:", reason)

                # Ошибка сайта НЕ считается исчезновением товара.
                if status == "error":
                    print("⚠️ Ошибка проверки. Состояние не изменяем.")

                else:

                    # Первая успешная проверка:
                    # просто запоминаем состояние.
                    if last_status is None:

                        last_status = status

                        print(
                            "Начальное состояние сохранено:",
                            status
                        )

                    # Товар появился
                    elif status == "in" and last_status == "out":

                        message = (
                            f"🟢 {PRODUCT_NAME} появилась в продаже!\n\n"
                            f"Pivoines Rivière\n"
                            f"🔗 {PRODUCT_URL}"
                        )

                        send_telegram(message)

                        last_status = "in"

                    # Товар закончился
                    elif status == "out" and last_status == "in":

                        message = (
                            f"🔴 {PRODUCT_NAME} закончилась.\n\n"
                            f"Pivoines Rivière\n"
                            f"🔗 {PRODUCT_URL}"
                        )

                        send_telegram(message)

                        last_status = "out"

                    else:
                        print(
                            "Состояние не изменилось — "
                            "Telegram не отправляем."
                        )

                print("Следующая проверка через 60 секунд.")
                print("================================")

                await asyncio.sleep(60)

        finally:
            await browser.close()


asyncio.run(main())
