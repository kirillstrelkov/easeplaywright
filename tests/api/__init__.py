from easeplaywright.browser import Browser


def is_headless(browser: Browser) -> bool:
    return browser.is_headless()
