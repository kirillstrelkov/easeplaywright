# easeplaywright

[![Test](https://github.com/kirillstrelkov/easeplaywright/actions/workflows/test.yml/badge.svg?branch=master&event=push)](https://github.com/kirillstrelkov/easeplaywright/actions/workflows/test.yml)

Playwright-based wrapper and test-automation toolkit. Provides a high-level `Browser` API and the [PageObject pattern](https://playwright.dev/python/docs/pom) on top of Playwright's sync API, without writing Playwright boilerplate.

**Features:**

- Supports Chromium, Firefox, and Edge (via Playwright)
- PageObject pattern
- Context manager and decorator APIs for browser lifecycle
- Python 3.9+

---

## Installation

### Pip

```shell
pip install easeplaywright
playwright install         # download browser binaries (once per machine)
```

### With uv

```shell
uv add easeplaywright
uv run playwright install
```

> Edge (`"edge"` / `"edge_headless"`) runs against a system-installed Microsoft Edge (via Playwright's `msedge` channel) — `playwright install` alone does not provision it.

---

## Usage

### Direct API

```python
from easeplaywright.browser import Browser

browser = Browser("gc")  # gc=Chromium, ff=Firefox, edge=Edge
browser.get("https://duckduckgo.com")
browser.type(by_name="q", text="playwright")
browser.click(by_id="search_button_homepage")
print(browser.get_text(by_css="h2.result__title"))
browser.quit()
```

Most `Browser` methods accept either a Playwright `Locator`, a raw selector string (`element=`), or a `by_*=` kwarg:

```python
browser.type(by_css="input[name='q']", text="playwright")
browser.click("#search_button_homepage")
```

### Context manager

```python
from easeplaywright.browser import browser_context

with browser_context("gc", headless=True) as browser:
    browser.get("https://duckduckgo.com")
    print(browser.get_title())
# browser.quit() called automatically; screenshot saved on exception
```

### Decorator

```python
from easeplaywright.browser import browser_decorator


@browser_decorator(browser_name="gc", headless=True)
def run_search(browser=None):
    browser.get("https://duckduckgo.com")
    browser.type(by_name="q", text="playwright")
```

### PageObject pattern

```python
from easeplaywright.base_page_object import BasePageObject


class DuckDuckGo(BasePageObject):
    def search(self, text):
        self.browser.get("https://duckduckgo.com")
        self.browser.type(by_name="q", text=text)
        self.browser.click(by_id="search_button_homepage")
```

### Test base class

```python
from easeplaywright.base_test import BaseTest


class MyTest(BaseTest):
    BROWSER_NAME = "gc"

    def test_title(self):
        self.browser.get("https://duckduckgo.com")
        assert "DuckDuckGo" in self.browser.get_title()
```

`BaseTest` handles browser setup/teardown and saves a screenshot on failure.

---

## Development

Requires [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just).

```shell
just init        # create .venv, install dependencies and Playwright browser binaries
just fmt         # ruff format
just fix         # ruff check --fix + pyright
just test        # run pytest
just bump minor  # bump version and create git tag (major / minor / patch)
```

---

## Dependencies

| Package              | Role                    |
| -------------------- | ----------------------- |
| playwright           | Browser automation core |
| loguru               | Logging                 |
| pytest / pytest-html | Test runner             |

---

## License

MIT — [easeplaywright/licenses/easeplaywright_license.txt](/easeplaywright/licenses/easeplaywright_license.txt)
