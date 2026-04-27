from typing import Dict, List

# Site-specific CSS selectors for major e-commerce platforms
SITE_SELECTORS: Dict[str, Dict[str, List[str]]] = {
    "amazon.com": {
        "product_name": [
            "#productTitle",
            "h1.a-size-large",
            ".product-title-word-break",
        ],
        "current_price": [
            ".a-price .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            "#corePrice_feature_div .a-offscreen",
            ".a-price-whole",
        ],
        "original_price": [
            ".a-price.a-text-price .a-offscreen",
            "#listPrice",
            ".a-text-price .a-offscreen",
        ],
        "availability": [
            "#availability span",
            "#outOfStock .a-color-price",
            ".a-size-medium.a-color-success",
        ],
        "rating": [
            "span.a-icon-alt",
            "#acrPopover .a-icon-alt",
        ],
        "review_count": [
            "#acrCustomerReviewText",
            "#acrCustomerReviewLink span",
        ],
        "seller": [
            "#sellerProfileTriggerId",
            "#merchant-info a",
        ],
    },
    "ebay.com": {
        "product_name": [
            ".x-item-title__mainTitle span",
            "h1.it-ttl",
            ".x-item-title span.ux-textspans",
        ],
        "current_price": [
            ".x-price-primary .ux-textspans",
            "#prcIsum",
            "#prcIsum_bidPrice",
        ],
        "original_price": [
            ".x-price-approx__price .ux-textspans",
            "#orgPrc",
        ],
        "availability": [
            ".d-quantity__availability",
            ".qtySubTxt",
        ],
        "seller": [
            ".x-sellercard-atf__info__about-seller a",
        ],
    },
    "walmart.com": {
        "product_name": [
            "[itemprop='name']",
            ".prod-ProductTitle",
            "h1[class*='heading']",
        ],
        "current_price": [
            "[itemprop='price']",
            ".price-characteristic",
            "[data-automation='buybox-price']",
        ],
        "original_price": [
            ".strike.gray",
            "[data-automation='buybox-was-price']",
        ],
        "availability": [
            "[data-automation='fulfillment-type']",
            ".prod-blitz-copy-message",
        ],
        "rating": [
            "[itemprop='ratingValue']",
            ".stars-reviews-count-node",
        ],
    },
    "bestbuy.com": {
        "product_name": [
            ".sku-title h1",
            "[class*='heading-5']",
            "h1.v-fw-regular",
        ],
        "current_price": [
            ".priceView-customer-price span",
            "[data-testid='customer-price']",
        ],
        "original_price": [
            ".pricing-price__regular-price",
            ".sr-only",
        ],
        "availability": [
            ".fulfillment-fulfillment-summary",
            "[data-automation='availability']",
        ],
        "rating": [
            ".c-review-average",
            "[class*='average-overall-rating']",
        ],
        "review_count": [
            ".c-reviews",
            "[class*='total-reviews']",
        ],
    },
    "target.com": {
        "product_name": [
            "h1[data-test='product-title']",
            "[data-test='product-title']",
        ],
        "current_price": [
            "[data-test='product-price']",
            ".h-text-lg.h-text-grayDark",
        ],
        "original_price": [
            "[data-test='product-regular-price']",
        ],
        "availability": [
            "[data-test='shippingBlock-availabilityMessage']",
        ],
        "rating": [
            "[data-test='ratings']",
        ],
    },
}

# Fallback generic selectors for unknown e-commerce sites
GENERIC_SELECTORS: Dict[str, List[str]] = {
    "product_name": [
        "h1",
        "[data-testid='product-title']",
        "[data-product-name]",
        ".product-name",
        ".product-title",
        "#product-title",
        ".item-name",
        "[itemprop='name']",
        ".pdp-title",
        "h1.title",
    ],
    "current_price": [
        "[data-price]",
        "[data-testid='price']",
        "[itemprop='price']",
        ".price",
        ".current-price",
        ".sale-price",
        "#price",
        ".product-price",
        ".offer-price",
        ".selling-price",
        "[class*='price--current']",
        "[class*='current_price']",
        "[class*='final-price']",
        ".price-box .price",
        ".woocommerce-Price-amount",
    ],
    "original_price": [
        ".original-price",
        ".was-price",
        ".list-price",
        ".regular-price",
        "[data-original-price]",
        "[class*='price--original']",
        ".crossed-price",
        "del[data-price]",
        "s.price",
        ".compare-price",
    ],
    "availability": [
        "[data-availability]",
        ".availability",
        ".stock-status",
        ".in-stock",
        ".out-of-stock",
        "[itemprop='availability']",
        ".product-availability",
    ],
    "rating": [
        "[itemprop='ratingValue']",
        "[data-rating]",
        ".rating",
        ".star-rating",
        ".review-score",
        ".average-rating",
    ],
    "review_count": [
        "[itemprop='reviewCount']",
        ".review-count",
        ".ratings-count",
        "[data-review-count]",
        ".number-of-reviews",
    ],
    "currency": [
        "[itemprop='priceCurrency']",
        "meta[itemprop='priceCurrency']",
    ],
    "seller": [
        ".seller-name",
        "[data-seller]",
        ".merchant-name",
    ],
}

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]
