async def check_product(browser, product):
    url = product["url"]

    page = None

    try:
        print("Відкриваю:", url)

        # НОВА СТОРІНКА ДЛЯ КОЖНОЇ ПЕРЕВІРКИ
        page = await browser.new_page()

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        text = await page.locator("body").inner_text()
        text_lower = text.lower()

        # =========================================
        # ЗАХИСТ САЙТУ
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
                    "Сторінка захисту сайту"
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

            for i in range(await buttons.count()):

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

        # =========================================
        # GRAEFSWINNING
        # =========================================

        if "graefswinning.be" in url.lower():

            return await check_graefswinning(page)

        # =========================================
        # УНІВЕРСАЛЬНИЙ АЛГОРИТМ
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

        # =========================================
        # ОСОБЛИВА ОБРОБКА ПАДІННЯ PAGE
        # =========================================

        error_text = repr(error)

        if "TargetClosedError" in error_text:

            return (
                "unknown",
                "Сторінка браузера впала під час перевірки. Наступна перевірка буде виконана заново."
            )

        return (
            "error",
            error_text
        )

    finally:

        # =========================================
        # ОБОВ'ЯЗКОВО ЗАКРИВАЄМО СТОРІНКУ
        # =========================================

        if page:

            try:
                await page.close()
            except Exception:
                pass
