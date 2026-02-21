"""
Tests for BS4ScraperAdapter.

External HTTP calls are mocked at the httpx.AsyncClient level.
_parse_staff_page is tested directly as a pure unit since it has no I/O.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from prospectkeeper.adapters.bs4_scraper_adapter import BS4ScraperAdapter


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def make_http_response(status_code: int = 200, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


def make_async_client_mock(staff_url_response=None, page_response=None):
    """
    Builds a mock httpx.AsyncClient context manager.
    staff_url_response: response returned by _guess_staff_url candidate GETs
    page_response: response returned by the staff page GET
    """
    client_mock = AsyncMock()

    if staff_url_response is not None and page_response is not None:
        # _guess_staff_url tries candidates; first 200 returns staff URL
        # page GET returns page_response
        client_mock.get.side_effect = [staff_url_response, page_response]
    elif staff_url_response is not None:
        client_mock.get.return_value = staff_url_response
    else:
        # All candidates return 404 — no staff URL found
        not_found = make_http_response(404)
        client_mock.get.return_value = not_found

    return client_mock


def patch_async_client(client_mock):
    """Context manager that patches httpx.AsyncClient to return client_mock."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ─────────────────────────────────────────────────────────────────────────────
# find_contact_on_district_site
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestFindContactOnDistrictSite:
    async def test_returns_failure_when_no_district_website(self):
        adapter = BS4ScraperAdapter()
        result = await adapter.find_contact_on_district_site(
            contact_name="Alice", organization="Org A", district_website=None
        )
        assert result.success is False
        assert result.error == "No district website provided"

    async def test_returns_failure_when_staff_url_not_found(self):
        """All URL candidates return 404 → no staff URL found."""
        adapter = BS4ScraperAdapter()
        client_mock = make_async_client_mock()  # all 404s
        async_client_cm = patch_async_client(client_mock)

        with patch(
            "prospectkeeper.adapters.bs4_scraper_adapter.httpx.AsyncClient",
            return_value=async_client_cm,
        ):
            result = await adapter.find_contact_on_district_site(
                contact_name="Alice",
                organization="Org A",
                district_website="https://org-a.com",
            )

        assert result.success is False
        assert "Could not locate" in result.error

    async def test_returns_failure_on_timeout(self):
        """
        httpx.TimeoutException → returns failure with 'Timeout' error.

        The first client.get() (a candidate probe in _guess_staff_url) returns 200 so
        that a staff URL is found.  The second client.get() (the actual page fetch)
        raises TimeoutException, which propagates to the outer except block.
        """
        import httpx

        adapter = BS4ScraperAdapter()
        client_mock = AsyncMock()
        client_mock.get.side_effect = [
            make_http_response(200),              # candidate probe → staff URL found
            httpx.TimeoutException("timed out"),  # page fetch → timeout
        ]
        async_client_cm = patch_async_client(client_mock)

        with patch(
            "prospectkeeper.adapters.bs4_scraper_adapter.httpx.AsyncClient",
            return_value=async_client_cm,
        ):
            result = await adapter.find_contact_on_district_site(
                contact_name="Alice",
                organization="Org A",
                district_website="https://org-a.com",
            )

        assert result.success is False
        assert result.error == "Timeout"

    async def test_returns_failure_on_generic_exception(self):
        """
        An unexpected exception on the page fetch → error message propagated.

        The first client.get() (candidate probe) returns 200 so that _guess_staff_url
        succeeds.  The second client.get() (page fetch) raises ConnectionError, which
        reaches the outer except Exception handler.
        """
        adapter = BS4ScraperAdapter()
        client_mock = AsyncMock()
        client_mock.get.side_effect = [
            make_http_response(200),    # candidate probe → staff URL found
            ConnectionError("refused"), # page fetch → generic error
        ]
        async_client_cm = patch_async_client(client_mock)

        with patch(
            "prospectkeeper.adapters.bs4_scraper_adapter.httpx.AsyncClient",
            return_value=async_client_cm,
        ):
            result = await adapter.find_contact_on_district_site(
                contact_name="Alice",
                organization="Org A",
                district_website="https://org-a.com",
            )

        assert result.success is False
        assert "refused" in result.error

    async def test_person_found_returns_success_with_person_found_true(self):
        """Name appears in HTML → person_found=True."""
        html = "<html><body><p>alice johnson - Director</p></body></html>"
        staff_resp = make_http_response(200)
        page_resp = make_http_response(200, text=html)
        client_mock = make_async_client_mock(staff_resp, page_resp)
        async_client_cm = patch_async_client(client_mock)

        adapter = BS4ScraperAdapter()
        with patch(
            "prospectkeeper.adapters.bs4_scraper_adapter.httpx.AsyncClient",
            return_value=async_client_cm,
        ):
            result = await adapter.find_contact_on_district_site(
                contact_name="Alice Johnson",
                organization="Org A",
                district_website="https://org-a.com",
            )

        assert result.success is True
        assert result.person_found is True

    async def test_person_not_found_returns_success_with_person_found_false(self):
        """Name not in HTML → person_found=False but success=True."""
        html = "<html><body><p>Bob Smith - Manager</p></body></html>"
        staff_resp = make_http_response(200)
        page_resp = make_http_response(200, text=html)
        client_mock = make_async_client_mock(staff_resp, page_resp)
        async_client_cm = patch_async_client(client_mock)

        adapter = BS4ScraperAdapter()
        with patch(
            "prospectkeeper.adapters.bs4_scraper_adapter.httpx.AsyncClient",
            return_value=async_client_cm,
        ):
            result = await adapter.find_contact_on_district_site(
                contact_name="Alice Johnson",
                organization="Org A",
                district_website="https://org-a.com",
            )

        assert result.success is True
        assert result.person_found is False

    async def test_evidence_url_set_when_staff_url_found(self):
        html = "<html><body><p>alice johnson - Director</p></body></html>"
        staff_resp = make_http_response(200)
        page_resp = make_http_response(200, text=html)
        client_mock = AsyncMock()
        # First candidate GET returns 200 (first candidate = /team)
        client_mock.get.side_effect = [staff_resp, page_resp]
        async_client_cm = patch_async_client(client_mock)

        adapter = BS4ScraperAdapter()
        with patch(
            "prospectkeeper.adapters.bs4_scraper_adapter.httpx.AsyncClient",
            return_value=async_client_cm,
        ):
            result = await adapter.find_contact_on_district_site(
                contact_name="Alice Johnson",
                organization="Org A",
                district_website="https://org-a.com",
            )

        assert result.evidence_url is not None
        assert "org-a.com" in result.evidence_url


# ─────────────────────────────────────────────────────────────────────────────
# _parse_staff_page — pure unit tests (no HTTP)
# ─────────────────────────────────────────────────────────────────────────────


class TestParseStaffPage:
    """Direct tests of the HTML parsing logic."""

    def setup_method(self):
        self.adapter = BS4ScraperAdapter()

    def test_name_in_page_returns_person_found_true(self):
        html = "<p>Jane Smith is our Director</p>"
        result = self.adapter._parse_staff_page(html, "Jane Smith", "https://org.com")
        assert result.success is True
        assert result.person_found is True

    def test_name_not_in_page_returns_person_found_false(self):
        html = "<p>Bob Jones is our Director</p>"
        result = self.adapter._parse_staff_page(html, "Jane Smith", "https://org.com")
        assert result.success is True
        assert result.person_found is False

    def test_name_matching_is_case_insensitive(self):
        html = "<p>JANE SMITH Director</p>"
        result = self.adapter._parse_staff_page(html, "jane smith", "https://org.com")
        assert result.person_found is True

    def test_evidence_url_preserved(self):
        html = "<p>Jane Smith Director</p>"
        result = self.adapter._parse_staff_page(html, "Jane Smith", "https://org.com/team")
        assert result.evidence_url == "https://org.com/team"

    def test_raw_text_is_context_around_name(self):
        html = "<p>Jane Smith is our Director of Operations</p>"
        result = self.adapter._parse_staff_page(html, "Jane Smith", "https://org.com")
        assert result.raw_text is not None
        assert "jane smith" in result.raw_text.lower()

    @pytest.mark.parametrize("keyword,html_fragment", [
        ("director",      "Jane Smith Director of Operations"),
        ("manager",       "Jane Smith Senior Manager"),
        ("vp",            "Jane Smith VP of Sales"),
        ("vice president","Jane Smith Vice President"),
        ("chief",         "Jane Smith Chief Technology Officer"),
        ("lead",          "Jane Smith Lead Engineer"),
        ("head of",       "Jane Smith Head of Product"),
    ])
    def test_title_extracted_for_known_keywords(self, keyword, html_fragment):
        html = f"<p>{html_fragment}</p>"
        result = self.adapter._parse_staff_page(html, "Jane Smith", "https://org.com")
        assert result.person_found is True
        assert result.current_title is not None

    def test_title_is_none_when_no_keyword_in_context(self):
        # Name in page but no title keyword nearby
        html = "<p>Jane Smith works here. Her phone is 555-1234.</p>"
        result = self.adapter._parse_staff_page(html, "Jane Smith", "https://org.com")
        assert result.person_found is True
        assert result.current_title is None

    def test_person_not_found_raw_text_is_truncated_snippet(self):
        long_text = "x " * 300
        html = f"<p>Bob Jones{long_text}</p>"
        result = self.adapter._parse_staff_page(html, "Alice", "https://org.com")
        assert result.person_found is False
        # raw_text[:500] slice applied
        assert len(result.raw_text) <= 500

    def test_strips_html_tags_before_search(self):
        html = "<h2>Jane <em>Smith</em></h2><p>Director</p>"
        result = self.adapter._parse_staff_page(html, "Jane Smith", "https://org.com")
        assert result.person_found is True
