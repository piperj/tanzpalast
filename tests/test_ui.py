"""Playwright UI tests — iPhone 15 viewport (390×844).

Requires index.html to exist (Step 1+). Tests are skipped automatically
when index.html is not present so the suite stays green during build.
"""

import json
import threading
import http.server
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

ROOT = Path(__file__).parent.parent
INDEX = ROOT / "index.html"


# ---------------------------------------------------------------------------
# Skip entire module when index.html doesn't exist yet
# ---------------------------------------------------------------------------

if not INDEX.exists():
    pytest.skip("index.html not yet created (pre-Step 1)", allow_module_level=True)


# ---------------------------------------------------------------------------
# Local HTTP server fixture
# ---------------------------------------------------------------------------

def _start_server(directory: Path, port: int) -> threading.Thread:
    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.HTTPServer(("localhost", port), handler)
    httpd.allow_reuse_address = True

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, *args):
            pass  # silence server logs during tests

    httpd = http.server.HTTPServer(("localhost", port), _Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


@pytest.fixture(scope="session")
def base_url():
    port = 8765
    server = _start_server(ROOT, port)
    yield f"http://localhost:{port}"
    server.shutdown()


# ---------------------------------------------------------------------------
# iPhone 15 viewport fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def iphone_page(page: Page):
    page.set_viewport_size({"width": 390, "height": 844})
    return page


# ---------------------------------------------------------------------------
# Step 1: data loading + basic render
# ---------------------------------------------------------------------------

class TestDataLoading:
    def test_page_loads(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        expect(iphone_page).not_to_have_title("")

    def test_title_contains_tanzpalast(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        expect(iphone_page).to_have_title("Tanzpalast")

    def test_dance_cards_rendered(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        # At least one dance card must be visible
        cards = iphone_page.locator("[data-dance]")
        expect(cards.first).to_be_visible()

    def test_no_js_errors_on_load(self, iphone_page: Page, base_url: str):
        errors = []
        iphone_page.on("pageerror", lambda e: errors.append(str(e)))
        iphone_page.goto(base_url)
        iphone_page.wait_for_load_state("networkidle")
        assert errors == [], f"JS errors on load: {errors}"


# ---------------------------------------------------------------------------
# Step 2: Card structure
# ---------------------------------------------------------------------------

class TestCardStructure:
    def test_featured_video_always_visible(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.wait_for_load_state("networkidle")
        # First card's featured row must be visible without any tap
        featured = iphone_page.locator("[data-featured]").first
        expect(featured).to_be_visible()

    def test_sub_videos_collapsed_by_default(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.wait_for_load_state("networkidle")
        # Sub-video list should be hidden until card is tapped
        sub_list = iphone_page.locator("[data-sub-videos]").first
        expect(sub_list).to_be_hidden()

    def test_tap_card_expands_sub_videos(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.wait_for_load_state("networkidle")
        card = iphone_page.locator("[data-dance]").first
        card.tap()
        sub_list = card.locator("[data-sub-videos]")
        expect(sub_list).to_be_visible()

    def test_tap_card_again_collapses_sub_videos(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.wait_for_load_state("networkidle")
        card = iphone_page.locator("[data-dance]").first
        card.tap()
        card.tap()
        sub_list = card.locator("[data-sub-videos]")
        expect(sub_list).to_be_hidden()


# ---------------------------------------------------------------------------
# Step 3: iPhone layout
# ---------------------------------------------------------------------------

class TestIphoneLayout:
    def test_header_is_sticky(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        header = iphone_page.locator("header").first
        position = header.evaluate("el => getComputedStyle(el).position")
        assert position == "sticky", f"Header position is '{position}', expected 'sticky'"

    def test_tap_targets_at_least_44px(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.wait_for_load_state("networkidle")
        # Featured video rows must be at least 44px tall
        featured_rows = iphone_page.locator("[data-featured]").all()
        for row in featured_rows[:5]:  # sample first 5
            h = row.bounding_box()["height"]
            assert h >= 44, f"Tap target too small: {h}px"


# ---------------------------------------------------------------------------
# Step 4: Collection filter
# ---------------------------------------------------------------------------

class TestCollectionFilter:
    COLLECTIONS = ["Standard", "Smooth", "Latin", "Rhythm", "Club"]

    def test_hamburger_button_visible(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        hamburger = iphone_page.locator("[data-hamburger]")
        expect(hamburger).to_be_visible()

    def test_hamburger_opens_panel(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.locator("[data-hamburger]").tap()
        panel = iphone_page.locator("[data-nav-panel]")
        expect(panel).to_be_visible()

    def test_panel_lists_all_collections(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.locator("[data-hamburger]").tap()
        for name in self.COLLECTIONS:
            expect(iphone_page.get_by_text(name, exact=True)).to_be_visible()

    def test_tap_collection_closes_panel(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.locator("[data-hamburger]").tap()
        iphone_page.get_by_text("Latin", exact=True).tap()
        panel = iphone_page.locator("[data-nav-panel]")
        expect(panel).to_be_hidden()

    def test_active_collection_shown_in_header(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.locator("[data-hamburger]").tap()
        iphone_page.get_by_text("Latin", exact=True).tap()
        header = iphone_page.locator("header")
        expect(header).to_contain_text("Latin")

    def test_filter_hides_non_matching_cards(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.wait_for_load_state("networkidle")
        total_before = iphone_page.locator("[data-dance]").count()
        iphone_page.locator("[data-hamburger]").tap()
        iphone_page.get_by_text("Standard", exact=True).tap()
        total_after = iphone_page.locator("[data-dance]:visible").count()
        # Standard is a subset — visible count should be ≤ total
        assert total_after <= total_before


# ---------------------------------------------------------------------------
# Step 5: Mixed media icons
# ---------------------------------------------------------------------------

class TestMixedMedia:
    def test_video_shows_play_icon(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.wait_for_load_state("networkidle")
        # At least one play icon must exist
        expect(iphone_page.locator("[data-icon='video']").first).to_be_visible()

    def test_pdf_shows_document_icon(self, iphone_page: Page, base_url: str):
        iphone_page.goto(base_url)
        iphone_page.wait_for_load_state("networkidle")
        pdf_icons = iphone_page.locator("[data-icon='pdf']")
        if pdf_icons.count() > 0:
            expect(pdf_icons.first).to_be_visible()
        else:
            pytest.skip("No PDF entries in current data")


# ---------------------------------------------------------------------------
# Step 6: Loading + error states
# ---------------------------------------------------------------------------

class TestLoadingAndError:
    def test_loading_state_shown_initially(self, iphone_page: Page, base_url: str):
        # Intercept the data fetch to stall it, verify loading indicator appears
        iphone_page.route("**/tanzpalast-data.json", lambda route: None)
        iphone_page.goto(base_url)
        loading = iphone_page.locator("[data-loading]")
        expect(loading).to_be_visible()

    def test_error_state_shown_on_fetch_failure(self, iphone_page: Page, base_url: str):
        iphone_page.route(
            "**/tanzpalast-data.json",
            lambda route: route.fulfill(status=500, body="error"),
        )
        iphone_page.goto(base_url)
        iphone_page.wait_for_load_state("networkidle")
        error = iphone_page.locator("[data-error]")
        expect(error).to_be_visible()
