"""Old Browser API tests: raw selector strings passed positionally instead of by_*= kwargs."""

from easeplaywright.base_test import BaseTest
from tests import EASEPLAYWRIGHT_TEST_URL


class BrowserTest(BaseTest):
    """Browser tests."""

    BROWSER_NAME = "gc"

    def test_get_parent(self) -> None:
        """Check get parent."""
        self.browser.get("https://duckduckgo.com/")

        element = self.browser.find_element(by_id="__next")
        parent = self.browser.get_parent(element)

        assert self.browser.get_tag_name(parent) == "body"

    def test_switch_to_frame(self) -> None:
        """Check switch to frame."""
        frame = "iframe[src*=default]"

        url = "https://www.w3schools.com/html/html_iframe.asp"
        frame_url = "https://www.w3schools.com/html/default.asp"

        self.browser.get(url)
        assert url == self.browser.get_current_frame_url()

        self.browser.switch_to_frame(frame)
        assert frame_url == self.browser.get_current_frame_url()

        self.browser.switch_to_default_content()
        assert url == self.browser.get_current_frame_url()

    def test_type_click_get_text(self) -> None:
        """Check type, click, get text."""
        self.browser.get("https://duckduckgo.com/")

        css_search_field = "input[class*='search-input']"
        css_search_btn = "button[data-mode='search']"
        css_results = "article h2"

        self.browser.type(css_search_field, "selenium python io")
        self.browser.click(css_search_btn)

        self.browser.wait_for_visible(css_results)
        assert "Selenium with Python" in self.browser.get_text(css_results)

    def test_mouse_left_right_clicks(self) -> None:
        """Check mouse left and right clicks."""
        self.browser.get("https://www.openstreetmap.org/")

        map_element = "#map"
        context_menu = "#map-context-menu .dropdown-menu"
        welcome_close = ".welcome .btn-close"

        self.browser.wait_for_visible(welcome_close)

        assert not self.browser.is_visible(context_menu)
        if self.browser.is_visible(welcome_close):
            self.browser.click(welcome_close)

        self.browser.mouse.right_click(map_element)
        self.browser.wait_for_visible(context_menu)

        self.browser.mouse.left_click_by_offset(map_element, -50, -50)
        self.browser.wait_for_not_visible(context_menu)

        self.browser.mouse.right_click_by_offset(map_element, 100, 100)
        self.browser.wait_for_visible(context_menu)

    def test_mouse_hover(self) -> None:
        """Check mouse hover."""
        self.browser.get("https://www.openstreetmap.org/")

        edit_buton = "#editanchor"
        tooltip = ".tooltip"

        self.browser.mouse.hover(edit_buton, force=True)
        self.browser.wait_for_visible(tooltip)
        assert "Zoom in" in self.browser.get_text(tooltip)

    def test_select(self) -> None:
        """Check select."""
        self.browser.get(EASEPLAYWRIGHT_TEST_URL)

        select_element = "select[name]"

        old_option = self.browser.get_selected_text_from_dropdown(select_element)
        self.browser.select_random_option_from_dropdown(
            select_element,
            texts_to_skip={old_option},
        )
        new_option = self.browser.get_selected_text_from_dropdown(select_element)
        new_option_value = self.browser.get_selected_value_from_dropdown(select_element)

        assert old_option != new_option
        assert new_option.lower().split(" ")[0] == new_option_value

        self.browser.select_option_by_index_from_dropdown(select_element, 0)

        new_option = "Second Value"
        self.browser.select_option_by_text_from_dropdown(select_element, new_option)
        assert self.browser.get_selected_text_from_dropdown(select_element) == new_option

        new_option = "third"
        self.browser.select_option_by_value_from_dropdown(select_element, new_option)
        assert self.browser.get_selected_value_from_dropdown(select_element) == new_option

        index = 0
        self.browser.select_option_by_index_from_dropdown(select_element, index)
        assert self.browser.get_selected_value_from_dropdown(select_element) == "first"
        index = 2
        self.browser.select_option_by_index_from_dropdown(select_element, index)
        assert self.browser.get_selected_value_from_dropdown(select_element) == "third"

        texts = self.browser.get_texts_from_dropdown(select_element)
        values = self.browser.get_values_from_dropdown(select_element)
        assert len(texts) == len(values)
        assert texts == ["First Value", "Second Value", "Third Value"]
        assert values == ["first", "second", "third"]

    def test_js_script(self) -> None:
        """Check JavaScript execution."""
        self.browser.get(EASEPLAYWRIGHT_TEST_URL)
        js_statement = "return document.getElementsByTagName('span')[0].textContent;"
        value = self.browser.execute_js(js_statement)

        assert value == "About dropdowns"

    def test_open_close_new_window(self) -> None:
        """Check open and close new window."""
        self.browser.get("https://html.com/attributes/a-target/")

        a_element = 'a[target="_blank"]'

        title_before_click = self.browser.get_title()
        self.browser.switch_to_new_window(self.browser.click, a_element)
        title_after_click = self.browser.get_title()

        assert title_before_click != title_after_click

        self.browser.close_current_window_and_focus_to_previous_one()
        title_after_close = self.browser.get_title()
        assert title_before_click == title_after_close

    def test_alerts(self) -> None:
        """Check alerts."""
        self.browser.get("https://duckduckgo.com/")
        js_statement = "window.alert_val = window.confirm('Confirm dialog');"

        # alert_accept()/alert_dismiss() must be armed *before* the action
        # that opens the dialog - see Browser.alert_accept() docstring.
        self.browser.alert_accept()
        self.browser.execute_js(js_statement)
        assert self.browser.execute_js("return window.alert_val;")

        self.browser.alert_dismiss()
        self.browser.execute_js(js_statement)
        assert not self.browser.execute_js("return window.alert_val;")

    def test_get_attribute(self) -> None:
        """Check get attribute."""
        self.browser.get("https://duckduckgo.com/")
        assert self.browser.get_attribute("a[class*='footer']", "href") == "/about"

    def test_get_attribute_with_parent(self) -> None:
        """Check get attribute with parent."""
        self.browser.get("https://duckduckgo.com/")
        parent = self.browser.find_element(by_tag="footer")
        assert (
            self.browser.get_attribute(
                "a[class*='footer']",
                "href",
                parent=parent,
            )
            == "/about"
        )

    def test_wait_for_attribute_is_changed_with_parent(self) -> None:
        """Check wait for attribute is changed with parent."""
        self.browser.get("https://material.angular.io/components/expansion/overview")

        css_parent = "#expansion-overview"
        self.browser.wait_for_visible(css_parent)
        parent = self.browser.find_element(by_css=css_parent)

        css_mat_accardion = "expansion-overview-example mat-expansion-panel"
        old_value = self.browser.get_class(css_mat_accardion, parent=parent)
        self.browser.click(css_mat_accardion, parent=parent)

        self.browser.wait_for_attribute_is_changed(
            css_mat_accardion,
            "class",
            old_value,
            parent=parent,
        )
        new_value = self.browser.get_class(css_mat_accardion, parent=parent)
        assert old_value != new_value
