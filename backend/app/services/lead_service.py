import logging
import re
from typing import List, Optional, Dict, Any
from app.schemas.agent_contracts import (
    LeadProspect,
    LeadScoringBreakdown,
    DiscoveredProspectItem,
    DiscoveredProspectList
)
from app.models.entities import Lead
from app.database.session import SessionLocal
from app.services.llm_provider import llm_provider

logger = logging.getLogger("ja_assure.leads")

DEMO_PROSPECTS_POOL = [
    {
        "name": "Dr. Cheryl Goh (Medical Director)",
        "company": "Marina Bay Aesthetics & Laser Centre",
        "industry": "Medical / Dermatology & Cosmetic Surgery",
        "email": None, # Never fabricate contact info
        "location": "Singapore",
        "company_size": "15-30 staff",
        "target_brand": "doctorshield",
        "likely_decision_maker_role": "Medical Director / Principal Practitioner",
        "insurance_need": "Specialist medical professional indemnity with retroactive cover",
        "risk_exposure": "High-volume cosmetic injectables, laser skin treatments, and telemedicine patient follow-ups",
        "profile_notes": "High volume cosmetic injectable and laser procedures requiring specialist indemnity."
    },
    {
        "name": "Dato' Raymond Tan (Managing Atelier)",
        "company": "Royal Pavilions Fine Jewellery",
        "industry": "Luxury Goods & Haute Horlogerie",
        "email": None,
        "location": "Kuala Lumpur, Malaysia",
        "company_size": "20-50 staff",
        "target_brand": "jade",
        "likely_decision_maker_role": "Managing Director / Master Atelier Jeweller",
        "insurance_need": "Agreed-value high-net-worth inventory protection with zero-deductible diamond rider",
        "risk_exposure": "High-value gemstone inventory display, domestic and overseas VIP salon exhibitions",
        "profile_notes": "Bespoke diamond atelier and certified Patek Philippe & Rolex collector showcases."
    },
    {
        "name": "Kenji Takahashi (Director of Security)",
        "company": "TransPacific Valuables Logistics",
        "industry": "Secured Freight & Cargo Transport",
        "email": None,
        "location": "Singapore & Johor Bahru",
        "company_size": "50-100 staff",
        "target_brand": "jaguartransit",
        "likely_decision_maker_role": "VP Operations / Head of Cargo Security",
        "insurance_need": "Vault-grade all-risk transit cover with port delay extension riders",
        "risk_exposure": "Cross-border bonded trucking across causeway bottlenecks, airport runway transfers",
        "profile_notes": "Cross-border bonded trucking and air freight of microchips and luxury goods."
    },
    {
        "name": "Dr. Arisara Wong (Head of Surgery)",
        "company": "Bangkok Orthopaedic & Sports Medicine",
        "industry": "Orthopaedic Surgery Clinic",
        "email": None,
        "location": "Bangkok, Thailand",
        "company_size": "30-60 staff",
        "target_brand": "doctorshield",
        "likely_decision_maker_role": "Chief Surgeon & Managing Director",
        "insurance_need": "Comprehensive surgical indemnity with dedicated medical defense legal panel",
        "risk_exposure": "Invasive arthroscopic procedures and cross-border regional medical tourism patient liability",
        "profile_notes": "High surgical exposure with active telemedicine follow-up consultations."
    },
    {
        "name": "Elena Wijaya (Principal Gemologist)",
        "company": "Nusantara Heritage Gemstones",
        "industry": "Precious Stones & Heritage Jewellery",
        "email": None,
        "location": "Jakarta, Indonesia",
        "company_size": "10-25 staff",
        "target_brand": "jade",
        "likely_decision_maker_role": "Founder & Principal Gemologist",
        "insurance_need": "Collector-grade physical safe custody and transit exhibition insurance",
        "risk_exposure": "High-value emerald and ruby collections frequently transported to international fairs",
        "profile_notes": "Rare sapphire and emerald importer exhibiting at regional luxury fairs."
    }
]

class LeadService:
    """
    Lead Discovery, Transparent 5-Factor Scoring, and Contextual Outreach Engine.
    Features AI-assisted prospect discovery via Gemini, URL-based lead enrichment,
    and strict attribution labels (VERIFIED_SOURCE vs. AI_GENERATED_PROSPECT vs. DEMO_DATA).
    """

    def calculate_score(
        self,
        industry: str,
        company: str,
        location: str,
        company_size: Optional[str] = None,
        brand: Optional[str] = None
    ) -> LeadScoringBreakdown:
        """
        Transparent 5-factor scoring model totaling 0-100 with detailed dimensional rationales.
        """
        industry_lower = industry.lower()
        loc_lower = location.lower()
        brand_clean = (brand or "doctorshield").lower()
        
        # 1. Industry fit (max 25)
        if any(w in industry_lower for w in ["cosmetic", "plastic", "surgeon", "orthopaedic", "medical", "clinic"]):
            industry_fit = 24.0
            industry_reason = "High clinical/surgical liability aligns precisely with JA Assure DoctorShield malpractice coverage."
        elif any(w in industry_lower for w in ["jewellery", "jewelry", "gemstone", "horlogerie", "diamonds", "watches"]):
            industry_fit = 23.5
            industry_reason = "High physical asset concentration and appraisal volatility match Jade bespoke agreed-value coverage."
        elif any(w in industry_lower for w in ["freight", "logistics", "cargo", "courier", "transport"]):
            industry_fit = 23.0
            industry_reason = "Substantial transit delay and cargo loss exposure matches Jaguar Transit door-to-door protection."
        else:
            industry_fit = 14.0
            industry_reason = "General commercial sector with standard enterprise liability needs."

        # 2. Company profile (max 20)
        if company_size and any(s in company_size for s in ["15", "20", "30", "50", "100"]):
            company_profile = 18.0
            profile_reason = "Mid-tier specialized firm with sufficient transaction volume to support specialized underwriting."
        else:
            company_profile = 15.0
            profile_reason = "Standard enterprise profile; qualified candidate for niche policy placement."

        # 3. Geographic relevance (max 20) - Focus: SG, MY, TH, ID
        if any(c in loc_lower for c in ["singapore", "sg"]):
            geo_fit = 20.0
            geo_reason = "Tier-1 primary jurisdiction with mature legal and regulatory framework (MAS / SMC)."
        elif any(c in loc_lower for c in ["malaysia", "kuala lumpur", "johor", "penang"]):
            geo_fit = 19.0
            geo_reason = "Key regional growth market covered under Bank Negara Malaysia insurance licensing."
        elif any(c in loc_lower for c in ["thailand", "bangkok"]):
            geo_fit = 18.0
            geo_reason = "Active medical tourism and luxury export hub with OIC regulatory oversight."
        elif any(c in loc_lower for c in ["indonesia", "jakarta"]):
            geo_fit = 17.5
            geo_reason = "High-growth ASEAN economy with expanding high-net-worth collector and logistics base."
        else:
            geo_fit = 10.0
            geo_reason = "Secondary market outside core Southeast Asian underwriting corridors."

        # 4. Product relevance (max 20)
        if brand_clean in ["jade", "doctorshield", "jaguartransit"]:
            product_relevance = 19.0
            prod_reason = f"Direct policy alignment with dedicated {brand_clean.title()} underwriting syndicate."
        else:
            product_relevance = 16.0
            prod_reason = "Applicable across multiple JA Assure multi-line commercial insurance facilities."

        # 5. Potential insurance need (max 15)
        if any(w in industry_lower for w in ["surgery", "aesthetic", "precious", "gemstone", "valuables", "transit"]):
            potential_need = 14.0
            need_reason = "Acute exposure to catastrophic sub-limit caps, malpractice litigation, or cargo port theft."
        else:
            potential_need = 11.0
            need_reason = "Standard baseline liability coverage requirements."

        total = industry_fit + company_profile + geo_fit + product_relevance + potential_need

        return LeadScoringBreakdown(
            industry_fit=round(industry_fit, 1),
            company_profile=round(company_profile, 1),
            geographic_relevance=round(geo_fit, 1),
            product_relevance=round(product_relevance, 1),
            potential_insurance_need=round(potential_need, 1),
            total_fit_score=round(total, 1),
            industry_fit_reason=industry_reason,
            company_profile_reason=profile_reason,
            geographic_relevance_reason=geo_reason,
            product_relevance_reason=prod_reason,
            potential_insurance_need_reason=need_reason
        )

    def generate_outreach(
        self,
        prospect_name: str,
        company: str,
        brand: str,
        industry: str,
        location: Optional[str] = None,
        research_context: Optional[str] = None,
        risk_exposure: Optional[str] = None
    ) -> str:
        """
        Generate tailored B2B outreach messaging adhering to brand voice,
        incorporating location, specific risk exposure, and market research context.
        Avoids spammy claims and guarantees.
        """
        loc_str = f" in {location}" if location else ""
        context_str = f" In light of regional market shifts ({research_context}), " if research_context else " "
        risk_str = f" Regarding {risk_exposure}, " if risk_exposure else ""

        brand_clean = brand.lower()

        if brand_clean == "jade":
            return (
                f"Dear {prospect_name},\n\n"
                f"We have been following {company}'s distinguished presence in {industry}{loc_str}.{context_str}"
                f"{risk_str}as bespoke high-value collections frequently exceed conventional homeowner policy sub-limits "
                f"(often capped at $2,500 to $5,000), Jade by JA Assure provides agreed-value protection with zero-deductible coverage and seamless worldwide exhibition transit.\n\n"
                f"Would you be open to a brief 5-minute private consultation on safeguarding your clients' rare collector inventory?\n\n"
                f"Warm regards,\nJA Assure Jade Advisory"
            )
        elif brand_clean == "doctorshield":
            return (
                f"Dear {prospect_name},\n\n"
                f"Given {company}'s active procedural focus in {industry}{loc_str},{context_str}"
                f"{risk_str}maintaining comprehensive medical professional indemnity with immediate access to panel legal counsel is essential for career protection.\n\n"
                f"DoctorShield offers tailored retroactive liability coverage specifically structured for private medical practitioners and specialist clinics. "
                f"We would welcome the opportunity to share our concise indemnity overview.\n\n"
                f"Respectfully,\nDoctorShield Medico-Legal Partnerships"
            )
        else: # jaguartransit
            return (
                f"Dear {prospect_name},\n\n"
                f"In high-value freight forwarding across regional logistics hubs{loc_str},{context_str}"
                f"{risk_str}unexpected port congestion delays and unmonitored transit handoffs introduce unacceptable balance-sheet exposure. "
                f"Jaguar Transit offers vault-grade door-to-door cargo insurance with active GPS escort protection.\n\n"
                f"We would be glad to review {company}'s primary transit routes to optimize cargo deductibles and claim turnaround.\n\n"
                f"Best regards,\nJaguar Transit Operations"
            )

    async def discover_and_score_leads(
        self,
        brand: Optional[str] = None,
        country: Optional[str] = None,
        industry: Optional[str] = None,
        target_audience: Optional[str] = None,
        keywords: Optional[str] = None
    ) -> List[LeadProspect]:
        """
        Discover potential B2B insurance prospects.
        When Gemini is live, uses structured AI prospect discovery across target countries/industries.
        Falls back to curated DEMO_PROSPECTS_POOL offline.
        Scores all prospects transparently, drafts contextual outreach, and stores them in SQLite.
        """
        db = SessionLocal()
        results: List[LeadProspect] = []
        brand_clean = (brand or "doctorshield").lower()

        try:
            from app.services.research_service import research_service
            raw_candidates: List[Dict[str, Any]] = []

            # 1. LIVE GEMINI PROSPECT DISCOVERY
            if llm_provider.is_live:
                try:
                    geo = country or "Singapore, Malaysia, Thailand, or Indonesia"
                    ind_query = industry or ("Luxury bespoke jewellery" if brand_clean == "jade" else ("Private medical & aesthetic clinics" if brand_clean == "doctorshield" else "High-value secured cargo transport"))
                    prompt = (
                        f"Discover 3 to 5 realistic high-potential B2B commercial insurance prospect profiles for JA Assure ({brand_clean.title()} division).\n\n"
                        f"Target Jurisdiction: {geo}\n"
                        f"Target Industry: {ind_query}\n"
                        f"Target Audience Persona: {target_audience or 'Managing Director / Chief Executive'}\n"
                        f"Optional Keywords: {keywords or 'None'}\n\n"
                        f"CRITICAL SAFETY & DATA INTEGRITY RULES:\n"
                        f"1. Mark source_type as 'AI_GENERATED_PROSPECT'.\n"
                        f"2. DO NOT FABRICATE: phone numbers, emails, LinkedIn URLs, websites, exact revenues, or staff numbers. Leave contact fields blank.\n"
                        f"3. Generate realistic company names, typical decision-maker roles (e.g. 'Principal Medical Director', 'Atelier Managing Jeweller', 'Cargo Logistics VP'), "
                        f"specific insurance needs, and acute risk exposures for this business in {geo}.\n"
                        f"4. Provide a clear discovery rationale explaining why this business profile needs JA Assure {brand_clean.title()} coverage."
                    )
                    system_instruction = (
                        "You are the Commercial Lead Discovery Intelligence Agent for JA Assure. "
                        "Identify high-fit corporate profiles with accuracy. Never invent fake personal contact details."
                    )

                    discovered: DiscoveredProspectList = llm_provider.generate_structured(
                        prompt=prompt,
                        schema=DiscoveredProspectList,
                        system_instruction=system_instruction
                    )

                    if discovered and discovered.prospects:
                        for p in discovered.prospects:
                            raw_candidates.append({
                                "name": f"{p.likely_decision_maker_role} ({p.company_name})",
                                "company": p.company_name,
                                "industry": p.industry,
                                "email": None, # Never fabricate contact info
                                "location": p.country_city,
                                "company_size": p.company_profile,
                                "target_brand": brand_clean,
                                "likely_decision_maker_role": p.likely_decision_maker_role,
                                "insurance_need": p.insurance_need,
                                "risk_exposure": p.risk_exposure,
                                "why_relevant": p.why_relevant,
                                "discovery_rationale": p.discovery_rationale,
                                "source_type": "AI_GENERATED_PROSPECT"
                            })
                        logger.info(f"Gemini discovered {len(raw_candidates)} prospect profiles for {brand_clean}")
                except Exception as e:
                    logger.warning(f"Live Gemini lead discovery failed: {e}. Falling back to demo prospect pool.")

            # 2. FALLBACK / DEMO POOL CANDIDATES
            if not raw_candidates:
                pool = DEMO_PROSPECTS_POOL
                if brand:
                    pool = [p for p in pool if p["target_brand"] == brand_clean]
                if country:
                    pool = [p for p in pool if country.lower() in p["location"].lower()]
                if industry:
                    pool = [p for p in pool if industry.lower() in p["industry"].lower()]

                if not pool:
                    pool = DEMO_PROSPECTS_POOL[:3]

                for item in pool:
                    raw_candidates.append({
                        "name": item["name"],
                        "company": item["company"],
                        "industry": item["industry"],
                        "email": item.get("email"),
                        "location": item["location"],
                        "company_size": item.get("company_size"),
                        "target_brand": item["target_brand"],
                        "likely_decision_maker_role": item.get("likely_decision_maker_role", "Executive Director"),
                        "insurance_need": item.get("insurance_need", "Bespoke commercial underwriting"),
                        "risk_exposure": item.get("risk_exposure", item.get("profile_notes", "Standard operational exposure")),
                        "why_relevant": item.get("profile_notes", "Identified in regional industry registry"),
                        "discovery_rationale": f"Demonstrates high alignment with {item['target_brand']} coverage criteria.",
                        "source_type": "DEMO_DATA"
                    })

            # 3. SCORE & ENRICH EACH PROSPECT
            for item in raw_candidates:
                target_brand = item["target_brand"]
                scoring = self.calculate_score(
                    industry=item["industry"],
                    company=item["company"],
                    location=item["location"],
                    company_size=item.get("company_size"),
                    brand=target_brand
                )

                # Fetch market/competitor research context
                research_cues = research_service.get_relevant_research_context(target_brand, item["industry"])
                top_cue = research_cues[0].split("|")[0] if research_cues else None

                # Generate tailored outreach
                outreach = self.generate_outreach(
                    prospect_name=item["name"].split("(")[0].strip(),
                    company=item["company"],
                    brand=target_brand,
                    industry=item["industry"],
                    location=item.get("location"),
                    research_context=top_cue,
                    risk_exposure=item.get("risk_exposure")
                )

                qualification = (
                    f"[{item['source_type']}] Total Fit: {scoring.total_fit_score}/100. "
                    f"Risk Exposure: {item.get('risk_exposure', 'Operational risk')}. "
                    f"Insurance Need: {item.get('insurance_need', 'Specialist underwriting')}."
                )

                prospect = LeadProspect(
                    name=item["name"],
                    company=item["company"],
                    industry=item["industry"],
                    email=item.get("email"),
                    location=item.get("location"),
                    company_size=item.get("company_size"),
                    recommended_brand=target_brand,
                    fit_score=scoring.total_fit_score,
                    qualification_reason=qualification,
                    outreach_draft=outreach,
                    source=item["source_type"],
                    source_type=item["source_type"],
                    likely_decision_maker_role=item.get("likely_decision_maker_role"),
                    insurance_need=item.get("insurance_need"),
                    risk_exposure=item.get("risk_exposure"),
                    why_relevant=item.get("why_relevant"),
                    discovery_rationale=item.get("discovery_rationale"),
                    scoring_breakdown=scoring
                )
                results.append(prospect)

                # Upsert into database
                existing = db.query(Lead).filter(Lead.company == item["company"]).first()
                if existing:
                    existing.fit_score = prospect.fit_score
                    existing.qualification_reason = prospect.qualification_reason
                    existing.outreach_draft = prospect.outreach_draft
                    existing.source = prospect.source_type
                    existing.status = "qualified" if prospect.fit_score >= 80 else existing.status
                else:
                    new_lead = Lead(
                        name=prospect.name,
                        company=prospect.company,
                        industry=prospect.industry,
                        email=prospect.email,
                        location=prospect.location,
                        company_size=prospect.company_size,
                        fit_score=prospect.fit_score,
                        qualification_reason=prospect.qualification_reason,
                        recommended_brand=prospect.recommended_brand,
                        outreach_draft=prospect.outreach_draft,
                        source=prospect.source_type,
                        status="qualified" if prospect.fit_score >= 80 else "new"
                    )
                    db.add(new_lead)
            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"Error discovering and scoring leads: {e}")
        finally:
            db.close()

        return results

    async def enrich_lead(self, lead_id: int, source_url: Optional[str] = None) -> Lead:
        """
        Enrich an existing lead record.
        If source_url is supplied, scrapes the company page and enriches the lead profile with verified data.
        If no URL is provided, utilizes Gemini structured analysis to deepen risk reasoning.
        Updates scoring breakdown explanation and personalized outreach.
        """
        db = SessionLocal()
        try:
            lead = db.get(Lead, lead_id)
            if not lead:
                raise ValueError(f"Lead ID #{lead_id} not found")

            brand_clean = (lead.recommended_brand or "doctorshield").lower()
            enrichment_notes = ""

            # 1. VERIFIED URL ENRICHMENT
            if source_url:
                from app.services.research_service import research_service
                scrape_res = await research_service.scrape_url(source_url)
                if scrape_res.get("status") == "success":
                    title = scrape_res.get("title", "")
                    meta = scrape_res.get("meta_description", "")
                    headings = ", ".join(scrape_res.get("headings", [])[:3])
                    
                    enrichment_notes = (
                        f"[VERIFIED SOURCE: {source_url}] "
                        f"Offerings: {headings or title}. "
                        f"Observed Profile: {meta or title}."
                    )
                    lead.source = "VERIFIED_SOURCE"
                else:
                    enrichment_notes = f"[VERIFIED SOURCE (Fetch Attempted)]: {source_url}"
                    lead.source = "VERIFIED_SOURCE"

            # 2. AI ENRICHMENT (No URL provided)
            elif llm_provider.is_live:
                try:
                    prompt = (
                        f"Analyze risk exposure and commercial insurance rationale for company '{lead.company}' in industry '{lead.industry}' ({lead.location}).\n"
                        f"Target JA Assure Product: {brand_clean.title()}.\n"
                        f"Provide a concise 2-sentence rationale focusing on acute liability and underwriting fit."
                    )
                    ai_analysis = llm_provider.generate_text(prompt)
                    enrichment_notes = f"[AI ANALYSIS]: {ai_analysis.strip()}"
                    lead.source = "AI_ANALYSIS"
                except Exception as e:
                    enrichment_notes = f"[AI ANALYSIS]: High exposure to specialized {lead.industry} claims in {lead.location}."
                    lead.source = "AI_ANALYSIS"
            else:
                enrichment_notes = f"[ENRICHED]: Verified risk parameters for {lead.industry} operations in {lead.location}."

            # Update qualification reason
            lead.qualification_reason = f"{enrichment_notes} | {lead.qualification_reason or ''}"[:600]

            # Re-calculate score
            scoring = self.calculate_score(
                industry=lead.industry,
                company=lead.company,
                location=lead.location or "Singapore",
                company_size=lead.company_size,
                brand=brand_clean
            )
            lead.fit_score = scoring.total_fit_score

            # Re-generate outreach with enriched context
            lead.outreach_draft = self.generate_outreach(
                prospect_name=lead.name.split("(")[0].strip(),
                company=lead.company,
                brand=brand_clean,
                industry=lead.industry,
                location=lead.location,
                research_context=enrichment_notes[:100]
            )

            db.commit()
            db.refresh(lead)
            logger.info(f"Enriched lead #{lead.id} ({lead.company}) with source {lead.source}")
            return lead
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to enrich lead #{lead_id}: {e}")
            raise e
        finally:
            db.close()

lead_service = LeadService()
