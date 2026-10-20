"""Public, source-linked data providers for Market and Industry Intelligence."""

from __future__ import annotations

import asyncio
import email.utils
import html
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config.settings import Settings, get_settings
from app.intelligence.industry import IndustryIntelligenceService


class _ArticleMetadata(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.description: str | None = None
        self.first_paragraph: str | None = None
        self._in_paragraph = False
        self._paragraph: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs}
        if tag.lower() == "meta":
            key = (values.get("name") or values.get("property") or "").casefold()
            if key in {"description", "og:description", "twitter:description"}:
                content = values.get("content")
                if content and len(content.strip()) > len(self.description or ""):
                    self.description = content.strip()
        elif tag.lower() == "p" and self.first_paragraph is None:
            self._in_paragraph = True
            self._paragraph = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p" and self._in_paragraph:
            value = " ".join(" ".join(self._paragraph).split())
            if len(value) >= 80:
                self.first_paragraph = value[:1200]
            self._in_paragraph = False

    def handle_data(self, data: str) -> None:
        if self._in_paragraph:
            self._paragraph.append(data)


class GdeltMarketProvider:
    """GDELT DOC API news search; it needs no API key and never synthesizes stories."""

    name = "GDELT DOC API / Google News RSS"

    def __init__(self, settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings or get_settings()
        self.transport = transport

    def is_available(self) -> bool:
        return self.settings.MARKET_INTELLIGENCE_PROVIDER.casefold() == "gdelt"

    async def fetch_events(self, company_name: str, company_id: str) -> list[dict[str, Any]]:
        if not self.is_available():
            return []
        query = f'"{company_name.replace(chr(34), " ").strip()}"'
        timeout = self.settings.GDELT_TIMEOUT_SECONDS
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, transport=self.transport) as client:
            try:
                response = await client.get(
                    self.settings.GDELT_DOC_API_URL,
                    params={"query": query, "mode": "artlist", "maxrecords": self.settings.GDELT_MAX_RECORDS,
                            "format": "json", "sort": "datedesc"},
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if self._is_temporary_failure(exc.response.status_code):
                    return await self._fallback_or_raise(
                        client, company_name, company_id, exc,
                        f"GDELT HTTP {exc.response.status_code}",
                    )
                raise
            except httpx.TransportError as exc:
                return await self._fallback_or_raise(
                    client, company_name, company_id, exc, f"GDELT {type(exc).__name__}"
                )

            # A valid empty GDELT response is distinct from a provider failure.
            # Query the configured secondary source before returning no results.
            try:
                payload = response.json()
                articles = payload.get("articles") if isinstance(payload, dict) else None
                if not isinstance(articles, list):
                    raise ValueError("GDELT returned an unexpected article-list response")
            except (ValueError, TypeError) as exc:
                return await self._fallback_or_raise(
                    client, company_name, company_id, exc, "GDELT response could not be parsed"
                )
            if not articles:
                if self.settings.MARKET_NEWS_RSS_FALLBACK:
                    return await self._google_news_events(
                        client, company_name, company_id, "GDELT returned no articles"
                    )
                return []

            semaphore = asyncio.Semaphore(5)

            async def enrich(article: Any) -> dict[str, Any] | None:
                if not isinstance(article, dict):
                    return None
                title = article.get("title")
                url = article.get("url")
                if not isinstance(title, str) or not title.strip() or not isinstance(url, str):
                    return None
                summary = await self._article_summary(client, semaphore, url)
                # The query is exact-name scoped; this guard prevents unrelated hits
                # from being presented as company news when a provider broadens a query.
                if not self._company_mentioned(company_name, f"{title} {summary or ''}"):
                    return None
                domain = article.get("domain") or urlparse(url).netloc
                raw_date = article.get("seendate")
                publication_date = None
                if isinstance(raw_date, str):
                    match = re.match(r"^(\d{4})(\d{2})(\d{2})T", raw_date)
                    if match:
                        publication_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                return {
                    "title": title.strip(), "source": str(domain), "source_url": url,
                    "publication_date": publication_date, "summary": summary,
                    "excerpt": summary or title.strip(), "company_name": company_name,
                    "provider": self.name, "metadata": {"company_id": company_id, "language": article.get("language")},
                }

            records = await asyncio.gather(*(enrich(article) for article in articles))
            normalized = [item for item in records if item is not None]
            if not normalized and self.settings.MARKET_NEWS_RSS_FALLBACK:
                return await self._google_news_events(
                    client, company_name, company_id, "GDELT returned no company-specific articles"
                )
            return normalized

    @staticmethod
    def _is_temporary_failure(status_code: int) -> bool:
        return status_code in {408, 425, 429} or status_code >= 500

    async def _fallback_or_raise(
        self,
        client: httpx.AsyncClient,
        company_name: str,
        company_id: str,
        cause: Exception,
        fallback_reason: str,
    ) -> list[dict[str, Any]]:
        if self.settings.MARKET_NEWS_RSS_FALLBACK:
            return await self._google_news_events(client, company_name, company_id, fallback_reason)
        raise cause

    async def _google_news_events(
        self, client: httpx.AsyncClient, company_name: str, company_id: str,
        fallback_reason: str,
    ) -> list[dict[str, Any]]:
        response = await client.get(
            self.settings.GOOGLE_NEWS_RSS_URL,
            params={"q": f'"{company_name}"', "hl": "en-US", "gl": "US", "ceid": "US:en"},
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        records = []
        for item in root.findall("./channel/item"):
            title = item.findtext("title")
            url = item.findtext("link")
            source_element = item.find("source")
            source = (source_element.text or "").strip() if source_element is not None else ""
            summary_html = item.findtext("description") or ""
            summary = " ".join(html.unescape(re.sub(r"<[^>]*>", " ", summary_html)).split()) or None
            if title and source:
                clean_title = re.sub(r"\s+-\s+[^-]+$", "", title).strip()
                if summary:
                    summary_headline = re.sub(rf"\s*{re.escape(source)}\s*$", "", summary, flags=re.IGNORECASE).rstrip(" -—")
                    if summary_headline.casefold() == clean_title.casefold():
                        summary = None
                title = clean_title
            if not title or not url or not source or not self._company_mentioned(company_name, f"{title} {summary or ''}"):
                continue
            raw_date = item.findtext("pubDate")
            published = None
            if raw_date:
                try:
                    published = email.utils.parsedate_to_datetime(raw_date).date().isoformat()
                except (TypeError, ValueError, OverflowError):
                    published = None
            records.append({
                "title": title.strip(), "source": source, "source_url": url,
                "publication_date": published, "summary": summary,
                "excerpt": summary or title.strip(), "company_name": company_name,
                "provider": "Google News RSS",
                "metadata": {
                    "company_id": company_id,
                    "publisher_url": source_element.get("url") if source_element is not None else None,
                    "fallback_reason": fallback_reason,
                },
            })
            if len(records) >= self.settings.GDELT_MAX_RECORDS:
                break
        return records

    @staticmethod
    def _company_mentioned(company_name: str, text: str) -> bool:
        ignored = {"company", "corporation", "corp", "inc", "limited", "ltd", "group", "holdings", "the"}
        tokens = [token for token in re.findall(r"[a-z0-9]+", company_name.casefold())
                  if len(token) >= 4 and token not in ignored]
        return bool(tokens and any(token in text.casefold() for token in tokens))

    @staticmethod
    async def _article_summary(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, url: str) -> str | None:
        if urlparse(url).scheme not in {"http", "https"}:
            return None
        try:
            async with semaphore:
                response = await client.get(url)
                if response.status_code == 429 or response.is_error:
                    return None
                parser = _ArticleMetadata()
                parser.feed(response.text[:1_500_000])
                summary = parser.description or parser.first_paragraph
                return html.unescape(summary).strip() if summary else None
        except (httpx.HTTPError, ValueError):
            return None


class _TextFromHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "ix:header"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "ix:header"} and self._skip:
            self._skip -= 1
        elif tag.lower() in {"p", "div", "br", "td", "tr", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


class SecEdgarIndustryProvider:
    """Build sector themes and peer signals from SEC 10-K risk-factor disclosures."""

    name = "SEC EDGAR peer 10-K filings"
    PEER_NAME_MARKERS = ("BANK", "BANCORP", "BANCO", "TRUST")
    CATEGORY_LABELS = {
        "REGULATORY": "Regulatory", "MARKET": "Market", "CREDIT": "Credit",
        "LIQUIDITY": "Liquidity", "OPERATIONAL": "Operational", "CYBER": "Cybersecurity",
        "LEGAL": "Legal", "MACROECONOMIC": "Macroeconomic",
    }

    def __init__(self, settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings or get_settings()
        self.transport = transport
        self._service = IndustryIntelligenceService()

    def is_available(self) -> bool:
        return (
            self.settings.INDUSTRY_INTELLIGENCE_PROVIDER.casefold() == "sec_edgar"
            and bool((self.settings.SEC_EDGAR_USER_AGENT or "").strip())
        )

    async def fetch_industry_data(self, company_name: str, industry: str) -> dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("SEC_EDGAR_USER_AGENT is required for compliant EDGAR requests")
        headers = {"User-Agent": self.settings.SEC_EDGAR_USER_AGENT or "", "Accept-Encoding": "gzip, deflate"}
        async with httpx.AsyncClient(timeout=self.settings.SEC_EDGAR_TIMEOUT_SECONDS,
                                     follow_redirects=True, headers=headers,
                                     transport=self.transport) as client:
            response = await client.get(self.settings.SEC_EDGAR_TICKERS_URL)
            response.raise_for_status()
            ticker_data = response.json()
            fields = ticker_data.get("fields", [])
            rows = ticker_data.get("data", [])
            try:
                cik_col, name_col = fields.index("cik"), fields.index("name")
            except ValueError as exc:
                raise ValueError("SEC ticker directory schema changed") from exc
            entries = [row for row in rows if isinstance(row, list) and len(row) > max(cik_col, name_col)]
            target = self._match_company(entries, name_col, company_name)
            if target is None:
                return {"themes": [], "peers": []}
            target_cik = str(target[cik_col]).zfill(10)
            target_submissions = await self._submissions(client, target_cik)
            sic = str(target_submissions.get("sic", ""))
            sic_description = str(target_submissions.get("sicDescription", industry))
            if not sic:
                return {"themes": [], "peers": []}

            candidates = [row for row in entries if row is not target and self._peer_name(row[name_col])]
            candidates = candidates[:self.settings.SEC_EDGAR_PEER_CANDIDATES]
            semaphore = asyncio.Semaphore(4)

            async def same_sic(row: list[Any]) -> tuple[list[Any], dict[str, Any]] | None:
                cik = str(row[cik_col]).zfill(10)
                try:
                    async with semaphore:
                        filing = await self._latest_10k(client, cik)
                    if filing and str(filing["sic"]) == sic:
                        return row, filing
                except (httpx.HTTPError, ValueError, KeyError):
                    return None
                return None

            matches = await asyncio.gather(*(same_sic(row) for row in candidates))
            peers_with_filings = [result for result in matches if result is not None]
            peers_with_filings = peers_with_filings[:self.settings.SEC_EDGAR_MAX_PEERS]
            peer_records: list[dict[str, Any]] = []
            category_evidence: dict[str, list[dict[str, Any]]] = {}
            for row, filing in peers_with_filings:
                peer_name = str(row[name_col])
                extracted = self._risk_categories(filing["risk_text"])
                peer_evidence = []
                for category, excerpts in extracted.items():
                    for excerpt in excerpts[:2]:
                        evidence = {
                            "source": peer_name,
                            "source_url": filing["url"],
                            "publication_date": filing["filing_date"],
                            "excerpt": excerpt,
                            "metadata": {"cik": str(row[cik_col]), "sic": sic, "form": "10-K"},
                        }
                        category_evidence.setdefault(category, []).append(evidence)
                        peer_evidence.append(evidence)
                if peer_evidence:
                    peer_records.append({
                        "company_id": str(row[cik_col]), "name": peer_name, "industry": sic_description,
                        "risk_categories": sorted(extracted), "evidence": peer_evidence,
                    })

            themes = []
            for category, evidence in sorted(category_evidence.items()):
                peer_ids = {item["metadata"]["cik"] for item in evidence}
                # An industry-wide theme requires the same risk category in at least
                # two independently filed peer reports.
                if len(peer_ids) < 2:
                    continue
                themes.append({
                    "name": f"{sic_description} {self.CATEGORY_LABELS.get(category, category)} risk disclosures",
                    "category": category, "source": f"SEC EDGAR {sic_description} peer 10-K filings",
                    "source_url": evidence[0]["source_url"], "publication_date": evidence[0]["publication_date"],
                    "excerpt": evidence[0]["excerpt"], "supporting_evidence": evidence,
                    "relevance_score": min(1.0, len(peer_ids) / 4.0),
                    "metadata": {"sic": sic, "sic_description": sic_description, "supporting_peer_count": len(peer_ids)},
                })
            return {"themes": themes, "peers": peer_records}

    async def _submissions(self, client: httpx.AsyncClient, cik: str) -> dict[str, Any]:
        url = self.settings.SEC_EDGAR_SUBMISSIONS_URL.format(cik=cik)
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("SEC submissions response was not an object")
        return data

    async def _latest_10k(self, client: httpx.AsyncClient, cik: str) -> dict[str, Any] | None:
        data = await self._submissions(client, cik)
        recent = data.get("filings", {}).get("recent", {})
        forms, accessions, dates, documents = (
            recent.get("form", []), recent.get("accessionNumber", []),
            recent.get("filingDate", []), recent.get("primaryDocument", []),
        )
        index = next((i for i, form in enumerate(forms) if form == "10-K"), None)
        if index is None or index >= min(map(len, (accessions, dates, documents))):
            return None
        accession = accessions[index].replace("-", "")
        document = documents[index]
        cik_int = str(int(cik))
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{document}"
        response = await client.get(url)
        response.raise_for_status()
        parser = _TextFromHtml()
        parser.feed(response.text[:15_000_000])
        text = " ".join(" ".join(parser.parts).split())
        risk_text = self._extract_risk_factors(text)
        if not risk_text:
            return None
        return {"sic": str(data.get("sic", "")), "url": url, "filing_date": dates[index],
                "risk_text": risk_text}

    @staticmethod
    def _extract_risk_factors(text: str) -> str:
        starts = list(re.finditer(r"item\s*1a\.?\s*risk factors", text, re.IGNORECASE))
        end_pattern = re.compile(r"item\s*1b\.?\s*(?:unresolved staff comments|other|not applicable)", re.IGNORECASE)
        for start in starts:
            tail = text[start.end():]
            end = end_pattern.search(tail)
            candidate = tail[:end.start()] if end else tail[:250_000]
            # Skip table-of-contents entries, which are usually only a page reference.
            if len(candidate) >= 50:
                return candidate[:250_000]
        return ""

    def _risk_categories(self, text: str) -> dict[str, list[str]]:
        sentences = [value.strip() for value in re.split(r"(?<=[.!?])\s+", text) if len(value.strip()) > 50]
        results: dict[str, list[str]] = {}
        for category, terms in self._service.CATEGORY_TERMS.items():
            label = category.value
            matched = [sentence[:1200] for sentence in sentences
                       if self._service._terms(sentence).intersection(self._service._terms(" ".join(terms)))]
            if matched:
                results[label] = matched[:2]
        return results

    @staticmethod
    def _match_company(entries: list[list[Any]], name_col: int, company_name: str) -> list[Any] | None:
        normalize = lambda value: re.sub(r"[^a-z0-9]", "", str(value).casefold())
        query = normalize(company_name)
        exact = [row for row in entries if normalize(row[name_col]) == query]
        if exact:
            return exact[0]
        candidates = [row for row in entries if query and query in normalize(row[name_col])]
        return candidates[0] if len(candidates) == 1 else None

    @classmethod
    def _peer_name(cls, name: Any) -> bool:
        normalized = str(name).upper()
        return any(marker in normalized for marker in cls.PEER_NAME_MARKERS)
