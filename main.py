import os
import asyncio
from playwright.async_api import async_playwright

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

PRODUCT_URL = "https://pivoinesriviere.com/produit/albert-crousse/"

async def check_product(page):
    await page.goto(
        PRODUCT_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    await page.wait_for_timeout(3000)

    text = await page.locator("body").inner_text()

    # Признаки отсутствия товара
    out_of_stock = [
        "Rupture de stock",
        "Notify me when available",
        "épuisée pour cette année",
    ]

    for phrase in out_of_stock:
        if phrase.lower() in text.lower():
            return False, phrase

    # Проверяем, есть ли реально доступный вариант
    buttons = page.locator(
        "button, input[type='submit'], a"
    )

    visible_buy_button = False

    for i in range(await buttons.count()):
        element = buttons.nth(i)

        try:
            if not await element.is_visible():
                continue

            element_text = (await element.inner_text()).strip().lower()

            if "ajouter au panier" in element_text:
                if await element.is_enabled():
                    visible_buy_button = True
                    break

        except Exception:
            continue

    if visible_buy_button:
        return True, "Ajouter au panier доступна"

    return False, "Кнопка покупки недоступна"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        try:
            available, reason = await check_product(page)

            print("================================")
            print("ALESIA")
            print("URL:", PRODUCT_URL)
            print("AVAILABLE:", available)
            print("REASON:", reason)
            print("================================")

        except Exception as e:
            print("CHECK ERROR:", repr(e))

        finally:
            await browser.close()


asyncio.run(main())
