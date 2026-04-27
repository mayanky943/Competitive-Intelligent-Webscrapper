import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from loguru import logger

from app.scrapers.base import BaseScraper
from app.scrapers.selectors import GENERIC_SELECTORS, SITE_SELECTORS


class AsyncPriceScraper(BaseScraper):

    def _get_site_selectors(self, url: str) -> Dict[str, List[str]]:
        domain = urlparse(url).netloc.replace("www.", "")
        for site_domain, selectors in SITE_SELECTORS.items():
            if site_domain in domain:
                return selectors
        return GENERIC_SELECTORS

    def _extract_text(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if not element:
                    continue
                # Prefer content/value attributes on meta/input elements
                for attr in ("content", "value", "data-price"):
                    val = element.get(attr)
                    if val and val.strip():
                        return val.strip()
                text = element.get_text(strip=True)
                if text:
                    return text
            except Exception:
                continue
        return None

    def _parse_price(self, price_str: Optional[str]) -> Optional[float]:
        if not price_str:
            return None
        # Strip currency symbols and whitespace, keep digits . and ,
        cleaned = re.sub(r"[^\d.,]", "", str(price_str))
        if not cleaned:
            return None
        # Resolve ambiguity: 1,234.56 vs 1.234,56
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Treat trailing 2-digit group after comma as decimals
            parts = cleaned.split(",")
            if len(parts[-1]) == 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        try:
            return round(float(cleaned), 2)
        except (ValueError, TypeError):
            return None

    def _parse_rating(self, rating_str: Optional[str]) -> Optional[float]:
        if not rating_str:
            return None
        # "4.5 out of 5" or "4.5/5"
        match = re.search(r"(\d+\.?\d*)\s*(?:out of|\/)\s*(\d+)", rating_str)
        if match:
            return round(float(match.group(1)) / float(match.group(2)) * 5, 2)
        match = re.search(r"(\d+\.?\d*)", rating_str)
        if match:
            val = float(match.group(1))
            # Normalise 0-100 scale to 0-5
            return round(val, 2) if val <= 5 else round(val / 100 * 5, 2)
        return None

    def _parse_review_count(self, count_str: Optional[str]) -> Optional[int]:
        if not count_str:
            return None
        cleaned = re.sub(r"[^\d]", "", count_str.replace(",", ""))
        try:
            return int(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

    def _infer_currency(self, soup: BeautifulSoup, url: str) -> str:
        domain = urlparse(url).netloc
        tld_currency_map = {
            ".co.uk": "GBP",
            ".uk": "GBP",
            ".ca": "CAD",
            ".au": "AUD",
            ".de": "EUR",
            ".eu": "EUR",
            ".fr": "EUR",
            ".es": "EUR",
            ".it": "EUR",
            ".jp": "JPY",
            ".in": "INR",
            ".br": "BRL",
            ".mx": "MXN",
        }
        for tld, currency in tld_currency_map.items():
            if domain.endswith(tld):
                return currency
        symbol_map = {
            "£": "GBP",
            "€": "EUR",
            "¥": "JPY",
            "₹": "INR",
            "C$": "CAD",
            "A$": "AUD",
            "R$": "BRL",
        }
        text = soup.get_text()
        for symbol, code in symbol_map.items():
            if symbol in text:
                return code
        return "USD"

    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract schema.org Product JSON-LD — most reliable source."""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                raw = script.string
                if not raw:
                    continue
                data = json.loads(raw)
                if isinstance(data, list):
                    data = next((d for d in data if d.get("@type") == "Product"), {})
                if data.get("@type") != "Product":
                    continue
                offers = data.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                aggregate = data.get("aggregateRating", {})
                return {
                    "product_name": data.get("name"),
                    "current_price": offers.get("price"),
                    "currency": offers.get("priceCurrency", "USD"),
                    "availability": (offers.get("availability") or "").split("/")[-1] or None,
                    "rating": aggregate.get("ratingValue"),
                    "review_count": aggregate.get("reviewCount"),
                }
            except (json.JSONDecodeError, AttributeError):
                continue
        return {}

    def _extract_open_graph(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Secondary fallback: OpenGraph meta tags."""
        result: Dict[str, Any] = {}
        og_map = {
            "og:title": "product_name",
            "product:price:amount": "current_price",
            "product:price:currency": "currency",
        }
        for prop, field in og_map.items():
            tag = soup.find("meta", property=prop)
            if tag and tag.get("content"):
                result[field] = tag["content"]
        return result

    async def scrape(
        self,
        url: str,
        custom_selectors: Optional[Dict[str, List[str]]] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        html = await self.fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        selectors = custom_selectors or self._get_site_selectors(url)

        # Layered extraction: JSON-LD → OpenGraph → CSS selectors
        structured = self._extract_structured_data(soup)
        og_data = self._extract_open_graph(soup) if not structured.get("current_price") else {}

        def pick(*values):
            return next((v for v in values if v is not None and str(v).strip()), None)

        def css(field: str) -> Optional[str]:
            sel_list = selectors.get(field) or GENERIC_SELECTORS.get(field, [])
            return self._extract_text(soup, sel_list)

        product_name = pick(structured.get("product_name"), og_data.get("product_name"), css("product_name"))

        raw_price = pick(structured.get("current_price"), og_data.get("current_price"), css("current_price"))
        current_price = self._parse_price(str(raw_price)) if raw_price else None

        original_price = self._parse_price(css("original_price"))

        discount_pct = None
        if current_price and original_price and original_price > current_price:
            discount_pct = round((1 - current_price / original_price) * 100, 1)

        struct_rating = structured.get("rating")
        rating = (
            self._parse_rating(str(struct_rating)) if struct_rating
            else self._parse_rating(css("rating"))
        )

        struct_review = structured.get("review_count")
        review_count = (
            self._parse_review_count(str(struct_review)) if struct_review
            else self._parse_review_count(css("review_count"))
        )

        currency = pick(
            structured.get("currency"),
            og_data.get("currency"),
            css("currency"),
            self._infer_currency(soup, url),
        )

        return {
            "url": url,
            "product_name": product_name,
            "current_price": current_price,
            "original_price": original_price,
            "currency": currency or "USD",
            "discount_percentage": discount_pct,
            "availability": pick(structured.get("availability"), css("availability")),
            "rating": rating,
            "review_count": review_count,
            "seller": css("seller"),
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "domain": urlparse(url).netloc,
                "used_structured_data": bool(structured),
                "scraper": "AsyncPriceScraper",
            },
        }
