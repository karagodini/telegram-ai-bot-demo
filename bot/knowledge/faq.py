"""Поиск ответа по FAQ.

Документ режется на секции ``## Заголовок``. У секции может быть строка
``keywords: слово, другое слово`` — она не показывается клиенту, но участвует
в поиске. Сравнение идёт по TF-IDF и косинусной близости. Окончания русских
слов слегка срезаются, чтобы «доставку» и «доставка» считались одним токеном.
Это не морфоанализатор: редкие формы лучше продублировать в ``keywords``.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

_TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё]{2,}")
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_KEYWORDS_RE = re.compile(r"^keywords:\s*(.+)$", re.IGNORECASE)

# Служебные слова не отличают одну статью от другой.
_STOPWORDS = frozenset(
    {
        "и",
        "в",
        "во",
        "на",
        "с",
        "со",
        "по",
        "для",
        "как",
        "что",
        "это",
        "а",
        "не",
        "к",
        "ко",
        "от",
        "из",
        "у",
        "о",
        "об",
        "за",
        "мы",
        "вы",
        "я",
        "ли",
        "же",
        "то",
        "бы",
        "до",
        "при",
        "или",
        "если",
        "ну",
        "да",
        "нет",
        "уже",
        "еще",
        "там",
        "тут",
        "так",
        "под",
        "над",
        "без",
        "про",
        "через",
        "чтобы",
        "можно",
        "мне",
        "нас",
        "вам",
        "вас",
        "меня",
        "мой",
        "моя",
        "мои",
        "ваш",
        "ваша",
        "ваши",
        "этот",
        "эта",
        "эти",
        "есть",
        "будет",
        "быть",
        "хочу",
        "нужно",
        "надо",
        "подскажите",
        "скажите",
        "пожалуйста",
        "здравствуйте",
        "добрый",
        "день",
        "привет",
        "the",
        "and",
        "for",
        "you",
        "your",
    }
)

# Длинные суффиксы раньше коротких.
_SUFFIXES: tuple[str, ...] = (
    "иями",
    "ями",
    "ами",
    "ого",
    "ему",
    "ому",
    "ыми",
    "ими",
    "ая",
    "яя",
    "ое",
    "ее",
    "ые",
    "ие",
    "ой",
    "ый",
    "ий",
    "ых",
    "их",
    "ам",
    "ям",
    "ов",
    "ев",
    "ом",
    "ем",
    "ах",
    "ях",
    "а",
    "я",
    "ы",
    "и",
    "е",
    "у",
    "ю",
    "о",
)


def _normalize(token: str) -> str:
    return token.lower().replace("ё", "е")


def stem(token: str) -> str:
    """Срезает типичное русское окончание, если после среза остаётся корень."""
    word = _normalize(token)
    if len(word) <= 4:
        return word
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(text):
        word = _normalize(raw)
        if word in _STOPWORDS or word.isdigit():
            continue
        stemmed = stem(word)
        if stemmed in _STOPWORDS or len(stemmed) < 2:
            continue
        tokens.append(stemmed)
    return tokens


def build_search_query(user_texts: Sequence[str]) -> str:
    """Короткий уточняющий вопрос склеивается с предыдущим.

    «А сроки?» само по себе почти не о чем. Если содержательных токенов мало,
    к запросу добавляется реплика пользователя до неё.
    """
    texts = [item.strip() for item in user_texts if item and item.strip()]
    if not texts:
        return ""
    last = texts[-1]
    if len(tokenize(last)) < 3 and len(texts) >= 2:
        return f"{texts[-2]} {last}"
    return last


@dataclass(frozen=True)
class FaqEntry:
    title: str
    body: str
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class FaqHit:
    entry: FaqEntry
    score: float


class FaqIndex:
    def __init__(self, entries: Sequence[FaqEntry]) -> None:
        if not entries:
            raise ValueError("База FAQ пустая")
        self.entries: list[FaqEntry] = list(entries)
        documents = [self._document_tokens(entry) for entry in self.entries]
        self._idf = self._build_idf(documents)
        self._vectors = [self._tfidf(tokens) for tokens in documents]
        self._norms = [_norm(vector) for vector in self._vectors]

    @staticmethod
    def _document_tokens(entry: FaqEntry) -> list[str]:
        # Заголовок и keywords повторяются: в них собрано намерение статьи,
        # а в длинном ответе полезный термин размывается.
        keyword_text = " ".join(entry.keywords)
        weighted = "\n".join((entry.title, entry.title, keyword_text, keyword_text, entry.body))
        return tokenize(weighted)

    @staticmethod
    def _build_idf(documents: Sequence[Sequence[str]]) -> dict[str, float]:
        doc_count = len(documents)
        frequency: dict[str, int] = {}
        for tokens in documents:
            for token in set(tokens):
                frequency[token] = frequency.get(token, 0) + 1
        return {
            token: math.log((1 + doc_count) / (1 + count)) + 1.0
            for token, count in frequency.items()
        }

    def _tfidf(self, tokens: Sequence[str]) -> dict[str, float]:
        if not tokens:
            return {}
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        length = float(len(tokens))
        return {
            token: (count / length) * self._idf.get(token, 0.0) for token, count in counts.items()
        }

    def search(self, query: str, limit: int = 3) -> list[FaqHit]:
        query_tokens = tokenize(query)
        if not query_tokens or limit <= 0:
            return []
        query_vector = self._tfidf(query_tokens)
        query_norm = _norm(query_vector)
        if query_norm == 0.0:
            return []

        hits: list[FaqHit] = []
        for entry, vector, norm in zip(self.entries, self._vectors, self._norms, strict=True):
            if norm == 0.0:
                continue
            dot = sum(weight * vector.get(token, 0.0) for token, weight in query_vector.items())
            score = dot / (query_norm * norm)
            if score > 0.0:
                hits.append(FaqHit(entry=entry, score=score))
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]

    def best(self, query: str, min_score: float) -> FaqHit | None:
        hits = self.search(query, limit=1)
        if not hits or hits[0].score < min_score:
            return None
        return hits[0]

    @classmethod
    def from_markdown(cls, text: str) -> FaqIndex:
        matches = list(_SECTION_RE.finditer(text))
        if not matches:
            raise ValueError("В FAQ нет секций, начинающихся с '##'")

        entries: list[FaqEntry] = []
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            title = match.group(1).strip()
            keywords, body = _split_keywords(text[start:end])
            if not title or not body:
                raise ValueError(f"Секция FAQ «{title or 'без названия'}» пустая")
            entries.append(FaqEntry(title=title, body=body, keywords=tuple(keywords)))
        return cls(entries)

    @classmethod
    def from_path(cls, path: Path) -> FaqIndex:
        file = Path(path)
        if not file.is_file():
            raise FileNotFoundError(f"Файл FAQ не найден: {file}")
        return cls.from_markdown(file.read_text(encoding="utf-8"))


def _split_keywords(raw: str) -> tuple[list[str], str]:
    keywords: list[str] = []
    body_lines: list[str] = []
    for line in raw.strip().splitlines():
        matched = _KEYWORDS_RE.match(line.strip())
        if matched and not keywords:
            keywords = [part.strip() for part in matched.group(1).split(",") if part.strip()]
            continue
        body_lines.append(line)
    body = "\n".join(body_lines).strip()
    return keywords, body


def _norm(vector: dict[str, float]) -> float:
    if not vector:
        return 0.0
    return math.sqrt(sum(value * value for value in vector.values()))
