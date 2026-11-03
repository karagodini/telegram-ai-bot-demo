"""База знаний и поиск по ней."""

from bot.knowledge.faq import FaqEntry, FaqHit, FaqIndex, build_search_query

__all__ = ["FaqEntry", "FaqHit", "FaqIndex", "build_search_query"]
