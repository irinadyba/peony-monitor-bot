import asyncio
from playwright.async_api import async_playwright

PRODUCT_NAME = "ALESIA"
PRODUCT_URL = "https://pivoinesriviere.com/produit/alesia/"


async def check_product(page):
    await page.goto(
        PRODUCT_URL,
        wait_until="domcontentloaded",
        timeout=60000
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
            return False, phrase

    # Проверяем доступную кнопку добавления в корзину
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
                    return True, "Ajouter au panier доступна"

        except Exception:
            continue

    return False, "Кнопка покупки недоступна"


async def main():
    print("БОТ ЗАПУЩЕН")
    print("Мониторинг:", PRODUCT_NAME)
    print("Интервал: 60 секунд")

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

                try:
                    available, reason = await check_product(page)

                    print("AVAILABLE:", available)
                    print("REASON:", reason)

                except Exception as error:
                    print("CHECK ERROR:", repr(error))

                print("Следующая проверка через 60 секунд.")
                print("================================")

                await asyncio.sleep(60)

        finally:
            await browser.close()


asyncio.run(main())

