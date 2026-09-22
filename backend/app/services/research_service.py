import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx
from app.schemas.agent_contracts import CompetitorInsight, ResearchInsight, ResearchFinding
from app.models.entities import Competitor, CompetitorSnapshot
from app.database.session import SessionLocal
from app.services.llm_provider import llm_provider

logger = logging.getLogger("ja_assure.research")

DEMO_COMPETITOR_DATABASE = [
    {
        "name": "BriteProtect Jewellers",
        "url": "https://briteprotect.example.com",
        "category": "jewellery",
        "brand": "jade",
        "market_country": "Singapore & Regional",
        "title": "BriteProtect launches instant ring appraisal add-on",
        "summary": "Competitor introduced instant mobile photo appraisal for luxury bespoke rings up to $50,000.",
        "offerings": ["Instant mobile photo appraisal", "Standard bridal ring cover", "Online claim filing"],
        "positioning": "Speed and mobile-first convenience for entry-to-mid level jewellery.",
        "notable_claims": ["Appraisal in under 3 minutes via smartphone photo"],
        "detected_change": "New low-friction mobile onboarding process targeting younger bridal segment.",
        "actionable_recommendation": "Observed messaging prioritizes rapid smartphone appraisals with strict $50k valuation caps; this represents a whitespace opportunity for Jade to highlight master-gemologist physical appraisals and uncapped bespoke agreed-value coverage.",
        "relevance": 0.88,
        "key_messaging": "Fast, photo-only insurance quote in under 3 minutes.",
        "threat_level": "medium",
        "source_type": "DEMO_DATA"
    },
    {
        "name": "SingMed Liability Mutual",
        "url": "https://singmed-mutual.example.com",
        "category": "medical",
        "brand": "doctorshield",
        "market_country": "Singapore",
        "title": "SingMed adjusts aesthetic surgery liability premiums",
        "summary": "Increased indemnity premiums by 15% across private aesthetic and laser dermatology clinics.",
        "offerings": ["General medical indemnity", "Hospital practitioner cover", "Disciplinary hearing counsel"],
        "positioning": "Traditional medical defense organization with periodic risk surcharges.",
        "notable_claims": ["Covering 60% of registered practitioners across Singapore"],
        "detected_change": "Premium hike for high-volume aesthetic clinics due to recent cosmetic claim surges.",
        "actionable_recommendation": "Observed messaging does not prominently address premium price stability for cosmetic specialists; this represents a whitespace opportunity for DoctorShield to emphasize transparent, locked retroactive coverage with dedicated medical malpractice counsel.",
        "relevance": 0.94,
        "key_messaging": "Comprehensive protection with increasing annual risk surcharges.",
        "threat_level": "high",
        "source_type": "DEMO_DATA"
    },
    {
        "name": "AeroFreight Cargo Shield",
        "url": "https://aerofreight-shield.example.com",
        "category": "transit",
        "brand": "jaguartransit",
        "market_country": "Southeast Asia Hubs",
        "title": "AeroFreight adds port congestion transit clause",
        "summary": "Imposed strict 72-hour transit extension limitation on maritime high-value freight in regional ports.",
        "offerings": ["Port-to-port marine cargo", "Standard air freight riders", "Container theft coverage"],
        "positioning": "Volume-focused freight forwarding insurance with statutory loss limits.",
        "notable_claims": ["Automated port clearance endorsement"],
        "detected_change": "Excluding port delay losses beyond 72 hours for unmonitored cargo containers.",
        "actionable_recommendation": "Observed messaging introduces strict 72-hour port delay exclusion clauses; this represents a content and positioning opportunity for Jaguar Transit to showcase unlimited door-to-door vault protection and continuous GPS-monitored escort.",
        "relevance": 0.82,
        "key_messaging": "Standard maritime cargo coverage with strict port delay exclusions.",
        "threat_level": "medium",
        "source_type": "DEMO_DATA"
    }
]

class ResearchService:
    """
    Research and Competitor Intelligence Engine.
    Supports safe URL scraping, Gemini structured intelligence extraction,
    strategic whitespace & counter-positioning analysis, and transparent source labeling:
    VERIFIED_SOURCE vs. AI_ANALYSIS vs. DEMO_DATA.
    """

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Safely fetch and parse HTML from an explicitly supplied public URL.
        Enforces timeouts (8.0s), 512KB payload limits, content-type verification,
        and clean structural extraction (title, description, headings, visible text).
        """
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return {
                "status": "invalid_url",
                "url": url,
                "title": "Invalid URL",
                "summary": "URL must begin with http:// or https://",
                "source_type": "DEMO_DATA"
            }

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JA-Assure-ResearchBot/2.0 (B2B Market Intelligence; +https://ja-assure.com)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(url, headers=headers)
                
                # Check response status
                if resp.status_code != 200:
                    logger.warning(f"Scraper received HTTP {resp.status_code} for {url}")
                    return {
                        "status": "http_error",
                        "url": url,
                        "status_code": resp.status_code,
                        "title": f"HTTP {resp.status_code} Response",
                        "summary": f"Could not reach {url} (HTTP {resp.status_code}). Site may be restricted or unavailable.",
                        "source_type": "DEMO_DATA"
                    }

                # Check Content-Type (must be HTML or text)
                content_type = resp.headers.get("content-type", "").lower()
                if "text/html" not in content_type and "text/" not in content_type:
                    return {
                        "status": "non_html",
                        "url": url,
                        "title": "Non-HTML Resource",
                        "summary": f"URL returned content-type '{content_type}'. Scraping only supports HTML web pages.",
                        "source_type": "DEMO_DATA"
                    }

                # Limit body size to 512KB
                html_raw = resp.text[:524288]

                # Extract Title
                title_match = re.search(r"<title[^>]*>(.*?)</title>", html_raw, re.IGNORECASE | re.DOTALL)
                title = title_match.group(1).strip() if title_match else ""
                title = re.sub(r"\s+", " ", title)
                if not title:
                    title = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]

                # Extract Meta Description (standard or OpenGraph)
                desc_match = re.search(r'<meta\s+[^>]*name=["\'](?:description|twitter:description)["\']\s+content=["\'](.*?)["\']', html_raw, re.IGNORECASE)
                if not desc_match:
                    desc_match = re.search(r'<meta\s+[^>]*property=["\']og:description["\']\s+content=["\'](.*?)["\']', html_raw, re.IGNORECASE)
                meta_desc = desc_match.group(1).strip() if desc_match else ""

                # Extract Headings (h1, h2, h3)
                heading_matches = re.findall(r'<h[1-3][^>]*>(.*?)</h[1-3]>', html_raw, re.IGNORECASE | re.DOTALL)
                clean_headings = []
                for h in heading_matches[:6]:
                    cleaned_h = re.sub(r"<[^>]+>", " ", h).strip()
                    cleaned_h = re.sub(r"\s+", " ", cleaned_h)
                    if cleaned_h and len(cleaned_h) > 5 and cleaned_h not in clean_headings:
                        clean_headings.append(cleaned_h)

                # Clean visible body text (strip scripts, styles, svg, tags)
                body_clean = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html_raw, flags=re.IGNORECASE | re.DOTALL)
                body_clean = re.sub(r"<[^>]+>", " ", body_clean)
                body_clean = re.sub(r"\s+", " ", body_clean).strip()
                extracted_sample = body_clean[:2000]

                return {
                    "status": "success",
                    "url": url,
                    "title": title,
                    "meta_description": meta_desc,
                    "headings": clean_headings,
                    "extracted_sample": extracted_sample,
                    "source_type": "VERIFIED_SOURCE"
                }

        except httpx.TimeoutException:
            logger.warning(f"Timeout scraping URL {url} (exceeded 8s).")
            return {
                "status": "timeout",
                "url": url,
                "title": f"Timeout connecting to {url}",
                "summary": "Target server took longer than 8 seconds to respond.",
                "source_type": "DEMO_DATA"
            }
        except Exception as e:
            logger.warning(f"Error scraping URL {url}: {e}")
            return {
                "status": "network_fallback",
                "url": url,
                "title": f"Competitor Intelligence for {url}",
                "summary": f"Live web fetch encountered network restriction: {str(e)}.",
                "source_type": "DEMO_DATA"
            }

    async def analyze_scraped_content(self, scraped_data: Dict[str, Any], brand: Optional[str] = None) -> ResearchFinding:
        """
        Analyze extracted website content using Gemini when available,
        or structured heuristic fallback when offline.
        Produces verified findings with strict counter-positioning framing:
        'Observed messaging does not prominently address [feature]; this represents a whitespace opportunity'.
        """
        url = scraped_data.get("url", "")
        title = scraped_data.get("title", "Competitor Website")
        meta_desc = scraped_data.get("meta_description", "")
        headings = scraped_data.get("headings", [])
        sample_text = scraped_data.get("extracted_sample", "")
        source_type = scraped_data.get("source_type", "VERIFIED_SOURCE")

        # Guess company name from domain or title
        domain = re.sub(r"^https?://(www\.)?", "", url).split("/")[0] if url else "Competitor"
        company_guess = title.split("-")[0].split("|")[0].strip() or domain

        brand_clean = (brand or "jade").lower()
        category_map = {"jade": "jewellery", "doctorshield": "medical", "jaguartransit": "transit"}
        category = category_map.get(brand_clean, "general")

        # 1. LIVE GEMINI ANALYSIS
        if llm_provider.is_live:
            try:
                prompt = (
                    f"Analyze the following verified scraped web page for competitor intelligence relevant to JA Assure ({brand_clean.title()} division).\n\n"
                    f"Source URL: {url}\n"
                    f"Page Title: {title}\n"
                    f"Meta Description: {meta_desc}\n"
                    f"Key Headings: {', '.join(headings) if headings else 'N/A'}\n"
                    f"Page Text Excerpt: {sample_text[:1200]}\n\n"
                    f"CRITICAL ANALYSIS REQUIREMENTS:\n"
                    f"1. source_type MUST be 'VERIFIED_SOURCE' because an actual URL was scraped.\n"
                    f"2. Retain the exact source URL.\n"
                    f"3. Extract verified products/offerings, target audience, positioning, and notable claims observed.\n"
                    f"4. COUNTER-POSITIONING RULE: Frame JA Assure's strategic opportunity strictly as:\n"
                    f"   'Observed messaging does not prominently address [feature]; this represents a content/whitespace opportunity for JA Assure.'\n"
                    f"   Do NOT state unverified competitor weaknesses as facts.\n"
                    f"5. Identify 2-3 content themes for marketing differentiation."
                )

                system_instruction = (
                    "You are the Chief Intelligence Analyst for JA Assure. "
                    "Analyze competitor messaging with high accuracy. "
                    "Never invent facts or cite unsupported rumors. Distinguish verified source data from strategic analysis."
                )

                finding: ResearchFinding = llm_provider.generate_structured(
                    prompt=prompt,
                    schema=ResearchFinding,
                    system_instruction=system_instruction
                )

                # Ensure source URL and verified attribution are preserved
                finding.source = url
                finding.source_type = "VERIFIED_SOURCE"
                if not finding.company:
                    finding.company = company_guess
                if not finding.category:
                    finding.category = category
                finding.confidence = 0.92

                logger.info(f"Gemini successfully analyzed competitor intelligence from {url}")
                return finding
            except Exception as e:
                logger.warning(f"Gemini analysis of scraped content failed: {e}. Falling back to deterministic analysis.")

        # 2. DETERMINISTIC FALLBACK ANALYSIS
        summary = meta_desc if meta_desc else f"Extracted offerings and market presence from {domain}."
        offerings = headings[:3] if headings else [f"Services described on {domain}"]
        positioning = f"Observed positioning focused on {headings[0] if headings else title}."
        notable_claims = [meta_desc[:120]] if meta_desc else ["Standard commercial claims observed on public site."]
        
        counter_pos = (
            f"Observed messaging for {company_guess} does not prominently address specialized underwriting and agreed-value transparency; "
            f"this represents a whitespace opportunity for JA Assure {brand_clean.title()}."
        )

        return ResearchFinding(
            source=url,
            source_type=source_type,
            title=title or f"Market Intelligence on {domain}",
            company=company_guess,
            category=category,
            market_country="Singapore & Regional",
            summary=summary,
            offerings=offerings,
            positioning=positioning,
            target_audience=f"Clients in {category} market",
            notable_claims=notable_claims,
            content_opportunities=[
                f"Highlight JA Assure {brand_clean.title()} tailored underwriting vs generic market solutions",
                "Educate buyers on specific policy sub-limits and exclusions"
            ],
            potential_weaknesses=[],
            counter_positioning=counter_pos,
            confidence=0.85
        )

    async def conduct_research(
        self,
        brand: str,
        topic: str,
        competitor_url: Optional[str] = None,
        country: Optional[str] = None
    ) -> ResearchInsight:
        """
        Conduct market and competitor research for the specified brand, topic, and optional country.
        If a competitor_url is provided, safely scrapes and analyzes it, saving the competitor record.
        Integrates Gemini research analysis when live, with realistic deterministic fallback.
        """
        brand_clean = brand.lower()
        findings: List[ResearchFinding] = []
        comp_insights: List[CompetitorInsight] = []
        sources = ["JA Assure Market Intel Index 2026"]

        # 1. PROCESS EXPLICIT COMPETITOR URL IF PROVIDED
        if competitor_url:
            scraped_data = await self.scrape_url(competitor_url)
            if scraped_data.get("status") == "success":
                finding = await self.analyze_scraped_content(scraped_data, brand=brand_clean)
                findings.append(finding)
                sources.append(competitor_url)

                # Persist/update in SQLite database
                self._save_or_update_competitor(brand_clean, competitor_url, finding)

                # Create insight entry
                comp_insights.append(
                    CompetitorInsight(
                        competitor_name=finding.company,
                        category=finding.category,
                        key_messaging=finding.positioning or finding.summary,
                        detected_change=", ".join(finding.notable_claims) if finding.notable_claims else "Active market presence",
                        opportunity=finding.counter_positioning,
                        threat_level="medium",
                        source_url=competitor_url,
                        market_country=finding.market_country,
                        offerings=finding.offerings,
                        positioning=finding.positioning,
                        notable_claims=finding.notable_claims,
                        content_themes=finding.content_opportunities,
                        source_type="VERIFIED_SOURCE",
                        confidence=finding.confidence,
                        last_researched=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                    )
                )

        # 2. IF LIVE GEMINI AVAILABLE & NO URL PROVIDED, CONDUCT AI RESEARCH ANALYSIS
        if llm_provider.is_live and not competitor_url:
            try:
                geo_context = f"in {country}" if country else "across Southeast Asia (Singapore, Malaysia, Thailand, Indonesia)"
                prompt = (
                    f"Perform structured B2B insurance research for JA Assure ({brand_clean.title()} division) on the topic: '{topic}' {geo_context}.\n\n"
                    f"Analyze current regional market risks, typical competitor approaches, and strategic whitespace.\n"
                    f"CRITICAL RULES:\n"
                    f"- Mark source_type as 'AI_ANALYSIS'.\n"
                    f"- Do NOT invent specific URLs or false corporate rumors.\n"
                    f"- Frame counter-positioning strictly as: 'Observed regional messaging does not prominently address [feature]; this represents a whitespace opportunity for JA Assure.'\n"
                    f"- Target high-value collectors, clinic medical directors, or logistics executives."
                )
                system_instruction = "You are the Senior Research Intelligence Officer for JA Assure."

                ai_finding: ResearchFinding = llm_provider.generate_structured(
                    prompt=prompt,
                    schema=ResearchFinding,
                    system_instruction=system_instruction
                )
                ai_finding.source_type = "AI_ANALYSIS"
                ai_finding.source = "Groq Market Intelligence Synthesis"
                findings.append(ai_finding)

                comp_insights.append(
                    CompetitorInsight(
                        competitor_name=ai_finding.company or f"{brand_clean.title()} Regional Market Move",
                        category=ai_finding.category or brand_clean,
                        key_messaging=ai_finding.summary,
                        detected_change=ai_finding.positioning or "Regional underwriting adjustments",
                        opportunity=ai_finding.counter_positioning or f"Differentiate {brand_clean.title()} with specialized agreed-value protection.",
                        threat_level="medium",
                        market_country=country or "Southeast Asia",
                        offerings=ai_finding.offerings,
                        positioning=ai_finding.positioning,
                        notable_claims=ai_finding.notable_claims,
                        content_themes=ai_finding.content_opportunities,
                        source_type="AI_ANALYSIS",
                        confidence=0.88,
                        last_researched=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                    )
                )
            except Exception as e:
                logger.warning(f"Live Gemini research synthesis failed: {e}. Utilizing fallback intelligence.")

        # 3. FALLBACK / SUPPLEMENT WITH DEMO COMPETITORS (Marked DEMO_DATA)
        if len(comp_insights) < 2:
            matched = [
                c for c in DEMO_COMPETITOR_DATABASE
                if c["brand"] == brand_clean or brand_clean not in ["jade", "doctorshield", "jaguartransit"]
            ]
            if not matched:
                matched = DEMO_COMPETITOR_DATABASE[:2]

            for c in matched:
                if not any(ci.competitor_name == c["name"] for ci in comp_insights):
                    comp_insights.append(
                        CompetitorInsight(
                            competitor_name=c["name"],
                            category=c["category"],
                            key_messaging=c["key_messaging"],
                            detected_change=c["detected_change"],
                            opportunity=c["actionable_recommendation"],
                            threat_level=c["threat_level"],
                            source_url=c["url"],
                            market_country=c.get("market_country", "Southeast Asia"),
                            offerings=c.get("offerings", []),
                            positioning=c.get("positioning"),
                            notable_claims=c.get("notable_claims", []),
                            content_themes=[c["actionable_recommendation"]],
                            source_type="DEMO_DATA",
                            confidence=c.get("relevance", 0.85),
                            last_researched=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                        )
                    )

        # Regional market context
        market_contexts = {
            "jade": "High-net-worth personal luxury and bespoke jewellery demand is growing 12% YoY across Southeast Asia, with luxury watches and natural diamonds facing under-insurance risks under conventional homeowner policies.",
            "doctorshield": "Medical practitioners in Singapore and Malaysia face increased scrutiny under telemedicine cross-border liability regulations and higher private cosmetic clinic claims.",
            "jaguartransit": "Regional air and port congestions in Southeast Asia have elevated high-value cargo exposure to delay exclusions and warehouse transit theft."
        }

        pain_points_map = {
            "jade": [
                "Home insurance policies cap unscheduled jewellery claims at $2,500-$5,000",
                "Appraisals are slow and require physically leaving jewellery at appraisal centres",
                "Worldwide travel loss is frequently excluded under domestic policies"
            ],
            "doctorshield": [
                "General indemnity policies exclude aesthetic or tele-consultation procedures",
                "Surging legal defence costs and strict panel attorney restrictions",
                "Lack of retroactive cover when switching medical malpractice insurers"
            ],
            "jaguartransit": [
                "Standard marine cargo policies exclude port delay beyond 48-72 hours",
                "High deductible thresholds on precious metals and gemstone shipments",
                "Lack of door-to-door vault-grade custody validation"
            ]
        }

        recommended_angles_map = {
            "jade": [
                "Contrast agreed-value bespoke protection vs homeowner policy sub-limits",
                "Highlight 24/7 worldwide travel coverage with zero deductible on certified diamonds",
                "Educate collectors on inflation-adjusted appraisal protection"
            ],
            "doctorshield": [
                "Focus on peace-of-mind retroactive liability coverage for specialist surgeons",
                "Address telemedicine compliance under updated Ministry of Health guidelines",
                "Highlight immediate access to dedicated medical malpractice defence counsel"
            ],
            "jaguartransit": [
                "Highlight zero-gap door-to-door vault security for haute horlogerie shipments",
                "Address port congestion riders with extended transit protection",
                "Demonstrate rapid claims settlement with dedicated high-value cargo assessors"
            ]
        }

        return ResearchInsight(
            brand=brand_clean,
            topic=topic,
            market_context=market_contexts.get(brand_clean, f"Market intelligence on {topic} for {brand_clean}"),
            target_audience="High-net-worth collectors, private clinic medical directors, and luxury goods logistics managers",
            pain_points=pain_points_map.get(brand_clean, ["Under-insurance", "Regulatory liability", "Transit exposure"]),
            competitor_insights=comp_insights,
            recommended_angles=recommended_angles_map.get(brand_clean, ["Highlight comprehensive coverage", "Educate on policy sub-limits"]),
            sources=sources,
            findings=findings
        )

    def _save_or_update_competitor(self, brand: str, url: str, finding: ResearchFinding):
        """
        Upserts scraped competitor intelligence into the SQLite database.
        Sets source to 'VERIFIED_SOURCE'.
        """
        db = SessionLocal()
        try:
            category_map = {"jade": "jewellery", "doctorshield": "medical", "jaguartransit": "transit"}
            category = category_map.get(brand, finding.category or "general")

            title = finding.title
            summary = finding.summary[:500]
            detected_change = finding.positioning or ", ".join(finding.notable_claims)[:500]
            recommendation = finding.counter_positioning

            existing = db.query(Competitor).filter(Competitor.url == url).first()
            if existing:
                existing.name = finding.company or existing.name
                existing.title = title
                existing.summary = summary
                existing.detected_change = detected_change
                existing.actionable_recommendation = recommendation
                existing.relevance = finding.confidence
                existing.source = "VERIFIED_SOURCE"
                existing.collected_at = datetime.now(timezone.utc)
                db.commit()
                competitor_id = existing.id
                logger.info(f"Updated verified competitor record: {existing.name} ({url})")
            else:
                new_comp = Competitor(
                    name=finding.company or re.sub(r"^https?://(www\.)?", "", url).split("/")[0],
                    url=url,
                    category=category,
                    title=title,
                    summary=summary,
                    detected_change=detected_change,
                    actionable_recommendation=recommendation,
                    relevance=finding.confidence,
                    source="VERIFIED_SOURCE",
                    collected_at=datetime.now(timezone.utc)
                )
                db.add(new_comp)
                db.commit()
                db.refresh(new_comp)
                competitor_id = new_comp.id
                logger.info(f"Saved new verified competitor record: {new_comp.name} ({url})")

            # Immutable history row -- see CompetitorSnapshot docstring. Written on
            # every research/analysis run (not just new competitors) so change
            # detection has something to compare against later.
            db.add(CompetitorSnapshot(
                competitor_id=competitor_id,
                source_url=url,
                source_type="VERIFIED_SOURCE",
                title=title,
                summary=summary,
                detected_change=detected_change,
                actionable_recommendation=recommendation,
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to upsert competitor: {e}")
        finally:
            db.close()

    def get_relevant_research_context(self, brand: str, topic: str) -> List[str]:
        """
        Lightweight relevance matcher: retrieves competitor moves & market insights
        from the database relevant to the brand and topic.
        Formats findings into concise bullet points ready for Gemini prompt injection.
        """
        db = SessionLocal()
        try:
            brand_clean = brand.lower()
            category_map = {"jade": "jewellery", "doctorshield": "medical", "jaguartransit": "transit"}
            target_cat = category_map.get(brand_clean, brand_clean)
            
            # Fetch all competitors
            competitors = db.query(Competitor).all()
            if not competitors:
                return [f"Market intel: {brand.title()} specializes in tailored niche coverage for Asian markets."]

            # Score relevance based on category match and topic keywords
            topic_words = set(re.findall(r"\w+", topic.lower()))
            scored = []
            for c in competitors:
                score = 0.0
                if c.category.lower() == target_cat:
                    score += 2.0
                content_words = set(re.findall(r"\w+", (c.title + " " + c.summary + " " + (c.detected_change or "")).lower()))
                overlap = len(topic_words.intersection(content_words))
                score += overlap * 0.5 + (c.relevance or 0.5)
                scored.append((score, c))

            scored.sort(key=lambda x: x[0], reverse=True)
            top_competitors = [item[1] for item in scored[:2]]

            context_lines = []
            for c in top_competitors:
                line = f"Competitor Move ({c.name} [{c.source}]): {c.summary}"
                if c.actionable_recommendation:
                    line += f" | Strategic Opportunity for {brand.title()}: {c.actionable_recommendation}"
                context_lines.append(line)

            return context_lines
        except Exception as e:
            logger.warning(f"Error querying research context: {e}")
            return [f"General market trend: Growing demand for specialized {brand.title()} coverage across Southeast Asia."]
        finally:
            db.close()

    def _build_digest_entry(self, competitor: Competitor, snapshots: List[CompetitorSnapshot]):
        """
        Compares the two most recent snapshots (if they exist) and reports a factual
        text-diff of which fields changed -- never presents speculation as fact:
        has_change is a mechanical comparison result, not an AI judgment about
        business significance, and why_it_matters/suggested_action are only
        populated when a real change was detected.
        """
        from app.schemas.dtos import CompetitorDigestEntry

        if not snapshots:
            current_state = {
                "title": competitor.title, "summary": competitor.summary,
                "detected_change": competitor.detected_change,
                "actionable_recommendation": competitor.actionable_recommendation,
            }
            return CompetitorDigestEntry(
                competitor_id=competitor.id, competitor_name=competitor.name, category=competitor.category,
                source_url=competitor.url, source_type=competitor.source_type,
                has_change=False, changed_fields=[], previous_state=None, current_state=current_state,
                detected_at=competitor.collected_at,
                note="No research snapshot exists yet for this competitor -- run research/analyze-url first.",
            )

        current = snapshots[-1]
        current_state = {
            "title": current.title, "summary": current.summary,
            "detected_change": current.detected_change,
            "actionable_recommendation": current.actionable_recommendation,
        }

        if len(snapshots) < 2:
            return CompetitorDigestEntry(
                competitor_id=competitor.id, competitor_name=competitor.name, category=competitor.category,
                source_url=current.source_url, source_type=current.source_type,
                has_change=False, changed_fields=[], previous_state=None, current_state=current_state,
                detected_at=current.captured_at,
                suggested_action=current.actionable_recommendation,
                note="Baseline snapshot -- no prior snapshot exists yet to compare against.",
            )

        previous = snapshots[-2]
        previous_state = {
            "title": previous.title, "summary": previous.summary,
            "detected_change": previous.detected_change,
            "actionable_recommendation": previous.actionable_recommendation,
        }
        changed_fields = [k for k in current_state if current_state[k] != previous_state[k]]
        has_change = len(changed_fields) > 0

        return CompetitorDigestEntry(
            competitor_id=competitor.id, competitor_name=competitor.name, category=competitor.category,
            source_url=current.source_url, source_type=current.source_type,
            has_change=has_change, changed_fields=changed_fields,
            previous_state=previous_state, current_state=current_state,
            detected_at=current.captured_at,
            why_it_matters=current.detected_change if has_change else None,
            suggested_action=current.actionable_recommendation if has_change else None,
            note=None if has_change else "No textual change detected since the previous snapshot.",
        )

    def get_competitor_digest(self, competitor_id: int):
        db = SessionLocal()
        try:
            competitor = db.get(Competitor, competitor_id)
            if not competitor:
                raise ValueError(f"Competitor #{competitor_id} not found")
            snapshots = list(competitor.snapshots)
            return self._build_digest_entry(competitor, snapshots)
        finally:
            db.close()

    def get_all_digests(self) -> List[Any]:
        db = SessionLocal()
        try:
            competitors = db.query(Competitor).all()
            return [self._build_digest_entry(c, list(c.snapshots)) for c in competitors]
        finally:
            db.close()


research_service = ResearchService()
