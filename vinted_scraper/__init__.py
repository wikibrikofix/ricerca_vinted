"""
vinted_scraper — scraper del catalogo Vinted basato su browser reale (Playwright).

API pubblica:
    from vinted_scraper import VintedScraper, Item
    from vinted_scraper.analysis import items_to_dataframe, summarize
"""
from .scraper import VintedScraper, Item, parse_title, CATEGORIES, LABELS

__all__ = ["VintedScraper", "Item", "parse_title", "CATEGORIES", "LABELS"]
__version__ = "1.0.0"
