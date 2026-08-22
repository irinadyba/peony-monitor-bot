import asyncio
import app
from site_detection import detect


# Сохраняем оригинальную проверку из app.py.
ORIGINAL_CHECK_PRODUCT = app.check_product


async def check_product(browser_manager, product):
    url = product["url"]
    supported = (
        "rottaler-pfingstrosen.de",
        "giessler-paeonien.de",
        "paeonyworld.pl",
        "peonypoland.pl",
        "peonyshop.com",
        "alexflowers.lv",
    )

    if any(domain in url.lower() for domain in supported):
        page = None
        try:
            print("[ADAPTIVE] Відкриваю:", url)
            page = await browser_manager.new_page()
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=app.PAGE_TIMEOUT,
            )
            await page.wait_for_timeout(app.PAGE_WAIT)

            body = (await page.locator("body").inner_text()).lower()
            protected = any(
                phrase in body
                for phrase in (
                    "just a moment",
                    "checking your browser",
                    "verify you are human",
                    "cf-chl",
                    "cloudflare",
                )
            )

            # Для Alex Flowers Cloudflare не является окончательной ошибкой:
            # site_detection.py проверит публичный WooCommerce Store API.
            if protected and "alexflowers.lv" not in url.lower():
                return "unknown", "Сторінка захисту сайту"

            result = await detect(page, url)
            if result is not None:
                print("[ADAPTIVE] Результат:", result)
                return result

        except Exception as error:
            print("[ADAPTIVE] Помилка:", repr(error))
            return "error", repr(error)
        finally:
            if page is not None:
                try:
                    await page.close()
                except Exception:
                    pass

    return await ORIGINAL_CHECK_PRODUCT(browser_manager, product)


# Підміняємо тільки функцію перевірки, а весь життєвий цикл бота
# (Telegram listener, моніторинг, збереження) залишаємо з app.py.
app.check_product = check_product


if __name__ == "__main__":
    asyncio.run(app.main())
