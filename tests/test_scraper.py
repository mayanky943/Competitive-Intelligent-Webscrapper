import pytest
from unittest.mock import AsyncMock

from app.scrapers.async_scraper import AsyncPriceScraper


@pytest.fixture
def scraper():
    return AsyncPriceScraper()


# ------------------------------------------------------------------
# Price parsing
# ------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("$29.99", 29.99),
    ("USD 1,234.56", 1234.56),
    ("€29,99", 29.99),
    ("£1.099,00", 1099.0),
    ("29", 29.0),
    (None, None),
    ("N/A", None),
    ("", None),
])
def test_parse_price(scraper, raw, expected):
    assert scraper._parse_price(raw) == expected


# ------------------------------------------------------------------
# Rating parsing
# ------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("4.5 out of 5 stars", 4.5),
    ("4.5/5", 4.5),
    ("4.5", 4.5),
    ("90", 4.5),   # 90/100 → 4.5/5
    (None, None),
])
def test_parse_rating(scraper, raw, expected):
    assert scraper._parse_rating(raw) == expected


# ------------------------------------------------------------------
# Review count parsing
# ------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("1,234 reviews", 1234),
    ("(567)", 567),
    ("42 ratings", 42),
    (None, None),
    ("no reviews", None),
])
def test_parse_review_count(scraper, raw, expected):
    assert scraper._parse_review_count(raw) == expected


# ------------------------------------------------------------------
# Currency inference
# ------------------------------------------------------------------

@pytest.mark.parametrize("url,expected", [
    ("https://amazon.co.uk/product", "GBP"),
    ("https://amazon.de/product", "EUR"),
    ("https://amazon.ca/product", "CAD"),
    ("https://amazon.com/product", "USD"),
])
def test_infer_currency_by_tld(scraper, url, expected):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup("<html></html>", "lxml")
    assert scraper._infer_currency(soup, url) == expected


# ------------------------------------------------------------------
# Structured data extraction
# ------------------------------------------------------------------

def test_extract_structured_data_product(scraper):
    from bs4 import BeautifulSoup
    html = """
    <html><head>
    <script type="application/ld+json">
    {
      "@type": "Product",
      "name": "Test Widget",
      "offers": {"@type": "Offer", "price": "49.99", "priceCurrency": "USD"},
      "aggregateRating": {"ratingValue": "4.3", "reviewCount": "120"}
    }
    </script>
    </head></html>
    """
    soup = BeautifulSoup(html, "lxml")
    data = scraper._extract_structured_data(soup)

    assert data["product_name"] == "Test Widget"
    assert data["current_price"] == "49.99"
    assert data["currency"] == "USD"
    assert data["rating"] == "4.3"
    assert data["review_count"] == "120"


# ------------------------------------------------------------------
# Full scrape with mocked fetch
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scrape_returns_result_on_valid_html():
    html = """
    <html><body>
      <h1>Awesome Gadget</h1>
      <span class="price">$19.99</span>
      <span class="original-price">$24.99</span>
    </body></html>
    """
    scraper = AsyncPriceScraper()
    scraper.fetch = AsyncMock(return_value=html)

    result = await scraper.scrape("https://shop.example.com/gadget")

    assert result is not None
    assert result["url"] == "https://shop.example.com/gadget"
    assert result["product_name"] == "Awesome Gadget"
    assert result["current_price"] == 19.99
    assert result["original_price"] == 24.99
    assert result["discount_percentage"] == pytest.approx(20.0, abs=0.5)


@pytest.mark.asyncio
async def test_scrape_returns_none_on_failed_fetch():
    scraper = AsyncPriceScraper()
    scraper.fetch = AsyncMock(return_value=None)

    result = await scraper.scrape("https://shop.example.com/missing")

    assert result is None
