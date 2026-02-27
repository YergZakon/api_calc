from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedArticle:
    article: str
    part: Optional[str] = None
    paragraph: Optional[str] = None
    code: Optional[str] = None
    raw: str = ""
    confidence: float = 1.0


class ArticleParser:
    PATTERNS = [
        r'(?:ст(?:атья)?\.?\s*)(\d+(?:-\d+)?)\s*(?:ч(?:асть)?\.?\s*(\d+))?\s*(?:п(?:ункт)?\.?\s*(\d+))?',
        r'^(\d+)[./\-](\d+)(?:[./\-](\d+))?$',
        r'^(\d{1,3})$',
    ]

    CODE_PATTERN = r'^(\d{7})$'

    @classmethod
    def parse(cls, text: str) -> Optional[ParsedArticle]:
        if not text:
            return None

        text = text.strip()

        if re.match(cls.CODE_PATTERN, text):
            return cls._parse_code(text)

        for pattern in cls.PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                article = groups[0]
                part = groups[1] if len(groups) > 1 and groups[1] else None
                paragraph = groups[2] if len(groups) > 2 and groups[2] else None
                return ParsedArticle(
                    article=article,
                    part=part,
                    paragraph=paragraph,
                    code=cls._build_code(article, part, paragraph),
                    raw=text,
                    confidence=0.9 if part else 0.8,
                )

        numbers = re.findall(r"\d+", text)
        if numbers:
            article = numbers[0]
            part = numbers[1] if len(numbers) > 1 else None
            paragraph = numbers[2] if len(numbers) > 2 else None
            return ParsedArticle(
                article=article,
                part=part,
                paragraph=paragraph,
                code=cls._build_code(article, part, paragraph),
                raw=text,
                confidence=0.5,
            )
        return None

    @classmethod
    def _parse_code(cls, code: str) -> ParsedArticle:
        article_raw = str(int(code[:3]))
        sub_article_raw = code[3:5]
        part_raw = code[5:7]

        if sub_article_raw != "00":
            article = f"{article_raw}-{int(sub_article_raw)}"
        else:
            article = article_raw

        part = str(int(part_raw)) if int(part_raw) > 0 else None

        return ParsedArticle(
            article=article,
            part=part,
            paragraph=None,
            code=code,
            raw=code,
            confidence=1.0,
        )

    @staticmethod
    def _build_code(article: str, part: Optional[str] = None, paragraph: Optional[str] = None) -> str:
        if not article:
            return ""

        match = re.match(r"^(\d+)(?:-(\d+))?$", str(article).strip())
        if match:
            art_num = match.group(1)
            sub_art = match.group(2) or "0"
        else:
            art_num = str(article)
            sub_art = "0"

        art = art_num.zfill(3)
        sub = sub_art.zfill(2)
        pt = str(part).zfill(2) if part else "01"
        return f"{art}{sub}{pt}"

    @classmethod
    def to_display_name(cls, article: str, part: Optional[str] = None, paragraph: Optional[str] = None) -> str:
        name = f"ст.{article}"
        if part:
            name += f" ч.{part}"
        if paragraph:
            name += f" п.{paragraph}"
        return name


def parse_article(text: str) -> Optional[ParsedArticle]:
    return ArticleParser.parse(text)
