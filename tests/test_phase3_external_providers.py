import httpx
import pytest
from datetime import date

from app.config.settings import Settings
from app.intelligence.external_providers import GdeltMarketProvider, SecEdgarIndustryProvider
from app.intelligence.industry import IndustryIntelligenceService
from app.intelligence.market import MarketIntelligenceService
from app.models.comparison import EvolutionChangeType, RiskEvolutionRecord


@pytest.mark.asyncio
async def test_gdelt_provider_maps_real_article_fields_and_publisher_description():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "gdelt.test":
            return httpx.Response(200, json={"articles": [{
                "title": "JPMorgan reports updated credit outlook",
                "url": "https://publisher.test/jpm-credit", "domain": "Publisher News",
                "seendate": "20260928T120000Z", "language": "English",
            }]})
        return httpx.Response(200, text='<html><meta property="og:description" content="Publisher supplied JPMorgan credit disclosure update."></html>')

    settings = Settings(DEBUG=False, GDELT_DOC_API_URL="https://gdelt.test/api", MARKET_INTELLIGENCE_PROVIDER="gdelt")
    provider = GdeltMarketProvider(settings, httpx.MockTransport(handler))
    events = await provider.fetch_events("JPMorgan", "company-id")
    assert provider.is_available()
    assert len(events) == 1
    assert events[0]["source"] == "Publisher News"
    assert events[0]["source_url"] == "https://publisher.test/jpm-credit"
    assert events[0]["publication_date"] == "2026-09-28"
    assert events[0]["summary"] == "Publisher supplied JPMorgan credit disclosure update."


@pytest.mark.asyncio
async def test_gdelt_rate_limit_is_reported_as_safe_unavailable_response():
    settings = Settings(DEBUG=False, GDELT_DOC_API_URL="https://gdelt.test/api", MARKET_NEWS_RSS_FALLBACK=False)
    provider = GdeltMarketProvider(settings, httpx.MockTransport(lambda request: httpx.Response(429)))
    assert provider.is_available()
    response = await MarketIntelligenceService(provider).fetch_for_company("company-id", "JPMorgan")
    assert response.events == []
    assert response.provider_available is False
    assert response.error == "Market provider unavailable: HTTPStatusError"


@pytest.mark.asyncio
async def test_real_google_news_rss_is_used_when_gdelt_rate_limits():
    rss = """<rss><channel><item><title>JPMorgan reports commercial credit update</title>
      <link>https://news.google.test/article/1</link>
      <description>&lt;p&gt;JPMorgan disclosed a commercial credit update.&lt;/p&gt;</description>
      <source url="https://publisher.test">Publisher News</source>
      <pubDate>Tue, 01 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>"""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "gdelt.test":
            return httpx.Response(429)
        return httpx.Response(200, text=rss, headers={"content-type": "application/rss+xml"})

    settings = Settings(DEBUG=False, GDELT_DOC_API_URL="https://gdelt.test/api",
                        GOOGLE_NEWS_RSS_URL="https://rss.test/search")
    provider = GdeltMarketProvider(settings, httpx.MockTransport(handler))
    result = await MarketIntelligenceService(provider).fetch_for_company("company-id", "JPMorgan")
    assert len(result.events) == 1
    event = result.events[0]
    assert event.source == "Publisher News"
    assert str(event.source_url) == "https://news.google.test/article/1"
    assert event.publication_date == date(2026, 9, 1)
    assert event.summary == "JPMorgan disclosed a commercial credit update."
    assert event.provider == "Google News RSS"
    assert event.evidence.metadata["fallback_reason"] == "GDELT HTTP 429"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [
    httpx.Response(503),
    httpx.ReadTimeout("GDELT timed out"),
])
async def test_gdelt_temporary_failures_use_configured_rss_fallback(failure):
    rss = """<rss><channel><item><title>JPMorgan liquidity disclosure</title>
      <link>https://news.google.test/liquidity</link><description>JPMorgan liquidity disclosure.</description>
      <source url="https://publisher.test">Publisher News</source>
      <pubDate>Tue, 01 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>"""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "gdelt.test":
            if isinstance(failure, Exception):
                raise failure
            return failure
        return httpx.Response(200, text=rss)

    settings = Settings(DEBUG=False, GDELT_DOC_API_URL="https://gdelt.test/api",
                        GOOGLE_NEWS_RSS_URL="https://rss.test/search")
    provider = GdeltMarketProvider(settings, httpx.MockTransport(handler))
    response = await MarketIntelligenceService(provider).fetch_for_company("company-id", "JPMorgan")
    assert response.provider_available is True
    assert len(response.events) == 1
    event = response.events[0]
    assert event.provider == "Google News RSS"
    assert str(event.source_url) == "https://news.google.test/liquidity"
    assert event.publication_date == date(2026, 9, 1)


@pytest.mark.asyncio
async def test_gdelt_genuine_empty_and_rss_empty_remain_a_successful_no_result():
    called = []

    def handler(request: httpx.Request) -> httpx.Response:
        called.append(request.url.host)
        if request.url.host == "gdelt.test":
            return httpx.Response(200, json={"articles": []})
        return httpx.Response(200, text="<rss><channel /></rss>")

    settings = Settings(DEBUG=False, GDELT_DOC_API_URL="https://gdelt.test/api",
                        GOOGLE_NEWS_RSS_URL="https://rss.test/search")
    provider = GdeltMarketProvider(settings, httpx.MockTransport(handler))
    response = await MarketIntelligenceService(provider).fetch_for_company("company-id", "JPMorgan")
    assert response.provider_available is True
    assert response.events == []
    assert called == ["gdelt.test", "rss.test"]


def sec_test_settings() -> Settings:
    return Settings(
        DEBUG=False,
        SEC_EDGAR_USER_AGENT="FinSight deterministic test analyst test@example.org",
        SEC_EDGAR_TICKERS_URL="https://sec.test/company_tickers_exchange.json",
        SEC_EDGAR_SUBMISSIONS_URL="https://sec.test/submissions/CIK{cik}.json",
        SEC_EDGAR_PEER_CANDIDATES=10,
        SEC_EDGAR_MAX_PEERS=4,
    )


@pytest.mark.asyncio
async def test_sec_edgar_filing_provider_requires_corroborated_peer_evidence():
    ticker_rows = [
        [19617, "JPMORGAN CHASE & CO", "JPM", "NYSE"],
        [11111, "FIRST NATIONAL BANK", "FNB", "NYSE"],
        [22222, "METRO BANK CORP", "MBC", "NYSE"],
        [33333, "UNRELATED SOFTWARE CORP", "USC", "NYSE"],
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("company_tickers_exchange.json"):
            return httpx.Response(200, json={"fields": ["cik", "name", "ticker", "exchange"], "data": ticker_rows})
        cik = request.url.path.rsplit("CIK", 1)[-1].removesuffix(".json")
        if "/Archives/" in request.url.path:
            excerpt = "Our cybersecurity program depends on third party vendors and security controls."
            return httpx.Response(200, text=f"<html><h2>Item 1A. Risk Factors</h2><p>{excerpt}</p><h2>Item 1B. Other Items</h2></html>")
        recent = {"form": ["10-K"], "accessionNumber": [f"0000000000-{cik}-000001"],
                  "filingDate": ["2026-02-01"], "primaryDocument": ["annual.html"]}
        return httpx.Response(200, json={"sic": "6021", "sicDescription": "National Commercial Banks",
                                         "filings": {"recent": recent}})

    provider = SecEdgarIndustryProvider(sec_test_settings(), httpx.MockTransport(handler))
    data = await provider.fetch_industry_data("JPMorgan", "Banking")
    assert provider.is_available()
    assert len(data["peers"]) == 2
    assert len(data["themes"]) == 1
    theme = data["themes"][0]
    assert theme["category"] == "CYBER"
    assert len({item["metadata"]["cik"] for item in theme["supporting_evidence"]}) == 2
    assert all(item["source_url"].startswith("https://www.sec.gov/Archives/") for item in theme["supporting_evidence"])
    normalized = IndustryIntelligenceService(provider).normalize_data(data, "jpm", "Banking")
    assert len(normalized["themes"][0].supporting_evidence) == 2


def test_industry_failure_and_unconfigured_sec_contact_do_not_claim_availability():
    settings = sec_test_settings().model_copy(update={"SEC_EDGAR_USER_AGENT": None})
    provider = SecEdgarIndustryProvider(settings)
    assert not provider.is_available()


def test_sec_risk_extractor_skips_table_of_contents_entry():
    from app.intelligence.external_providers import SecEdgarIndustryProvider

    text = (
        "Item 1A. Risk Factors ... 10-37 Item 1B. Unresolved Staff Comments. "
        "Item 1A. Risk Factors "
        + ("The Firm faces material credit, cybersecurity, operational, and regulatory risks. " * 8)
        + "Item 1B. Unresolved Staff Comments."
    )
    extracted = SecEdgarIndustryProvider._extract_risk_factors(text)
    assert "material credit" in extracted
    assert "10-37" not in extracted


@pytest.mark.asyncio
async def test_sec_rate_limit_returns_empty_unavailable_provider_result():
    provider = SecEdgarIndustryProvider(
        sec_test_settings(), httpx.MockTransport(lambda request: httpx.Response(429))
    )
    result = await IndustryIntelligenceService(provider).analyze_company(
        "company", "JPMorgan", "Banking"
    )
    assert result.themes == []
    assert result.peers == []
    assert result.provider_available is False
    assert result.provider == "SEC EDGAR peer 10-K filings"
    assert result.error == "Industry provider unavailable: HTTPStatusError"


def test_external_peer_evidence_can_be_used_by_existing_industry_assessment():
    peer_evidence = [
        {"source": "Bank One", "source_url": "https://sec.gov/a", "publication_date": "2026-02-01",
         "excerpt": "Cybersecurity vendor risks are described.", "metadata": {"cik": "1"}},
        {"source": "Bank Two", "source_url": "https://sec.gov/b", "publication_date": "2026-02-02",
         "excerpt": "Cybersecurity controls and risks are described.", "metadata": {"cik": "2"}},
    ]
    class Provider:
        name = "SEC EDGAR test"
        def is_available(self): return True
        async def fetch_industry_data(self, company_name, industry): return {"themes": [{
            "name": "Banking cybersecurity risk disclosures", "source": peer_evidence[0]["source"],
            "source_url": peer_evidence[0]["source_url"], "publication_date": peer_evidence[0]["publication_date"],
            "excerpt": peer_evidence[0]["excerpt"], "supporting_evidence": peer_evidence,
        }], "peers": []}

    service = IndustryIntelligenceService(Provider())
    risk = RiskEvolutionRecord(
        year_2_risk_id="risk-y2", change_type=EvolutionChangeType.MODIFIED,
        metadata={"title_y2": "Cybersecurity vendor exposure", "category": "Cybersecurity"},
    )
    result = __import__("asyncio").run(service.analyze_company("company", "JPMorgan", "Banking", [risk]))
    assert result.assessments[0].classification == "INDUSTRY_WIDE"
    assert {e.source for e in result.assessments[0].evidence} == {"Bank One", "Bank Two"}
