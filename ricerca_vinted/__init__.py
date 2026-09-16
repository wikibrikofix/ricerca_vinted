"""
ricerca_vinted — scraper del catalogo Vinted basato su browser reale (Playwright).

API pubblica:
    from ricerca_vinted import VintedScraper, Item
    from ricerca_vinted.analysis import items_to_dataframe, summarize
"""
from .scraper import VintedScraper, Item, parse_title, CATEGORIES, LABELS
from .quality import analyze, analyze_item, QualityReport

__all__ = ["VintedScraper", "Item", "parse_title", "CATEGORIES", "LABELS",
           "analyze", "analyze_item", "QualityReport"]
__version__ = "1.1.0"
