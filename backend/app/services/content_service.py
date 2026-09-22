import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.schemas.agent_contracts import ContentBrief, GeneratedVariation
from app.services.llm_provider import llm_provider
from app.services.lessons_service import lessons_service
from app.services.media_service import media_service

logger = logging.getLogger("ja_assure.content")

BRAND_PERSONAS = {
    "jade": {
        "title": "Jade Jewellery & Haute Horlogerie Insurance",
        "tone": "Luxury, highly precise, reassuring, collector-centric, and expert.",
        "voice_directives": (
            "Speak directly to discerning luxury collectors, bespoke jewellery connoisseurs, and high-net-worth watch owners. "
            "Highlight agreed-value valuation, certified gemologist appraisals, zero depreciation deductions, and worldwide transit protection. "
            "Never sound like a mass-market retailer; write with quiet luxury, connoisseur authority, and discretion."
        ),
        "disclaimer": "*Terms, conditions, and underwriting limits apply. Jade is a product underwritten by licensed partner insurers.*"
    },
    "doctorshield": {
        "title": "DoctorShield Medical Professional Indemnity",
        "tone": "Clinical, calm, deeply trustworthy, empathetic, and compliance-first.",
        "voice_directives": (
            "Speak directly to private specialist surgeons, aesthetic physicians, and clinic directors. "
            "Focus on peace of mind, career longevity, dedicated panel defence counsel, and seamless retroactive liability coverage. "
            "CRITICAL: Never offer clinical diagnosis or patient treatment advice; focus entirely on legal protection, indemnity limits, and medico-legal certainty."
        ),
        "disclaimer": "*DoctorShield is a professional medical indemnity policy underwritten by licensed partner insurers. Terms and conditions apply.*"
    },
    "jaguartransit": {
        "title": "Jaguar Transit High-Value Cargo Insurance",
        "tone": "Reliable, commanding, security-obsessed, results-oriented, and logistics-focused.",
        "voice_directives": (
            "Speak to supply chain directors, bonded courier logistics heads, and precious freight handlers. "
            "Emphasize door-to-door vault-grade custody, active GPS escort tracking, port congestion mitigation riders, and 24-hour claim resolution. "
            "Focus on eliminating supply chain balance sheet volatility."
        ),
        "disclaimer": "*Jaguar Transit cargo transit insurance is underwritten by licensed partner insurers. Terms and conditions apply.*"
    }
}

PLATFORM_SPECS = {
    "linkedin": {
        "max_length": 1500,
        "style": "Executive thought-leadership, structured with whitespace and bullet points, professional CTA."
    },
    "instagram": {
        "max_length": 600,
        "style": "Visual storytelling hook, evocative caption, 4-6 curated niche hashtags, link in bio CTA."
    },
    "blog": {
        "max_length": 2500,
        "style": "Comprehensive educational article with H2 subheadings, expert analysis, and thorough disclaimers."
    },
    "x": {
        "max_length": 280,
        "style": "Punchy hook, concise insight under 280 characters, compelling link CTA."
    },
    "reel": {
        "max_length": 800,
        "style": "Short-form video script with scene-by-scene audio/visual hooks and on-screen text."
    }
}

class ContentService:
    """
    Multi-Brand, Multi-Format, A/B Variation Content Generation Engine.
    Injects dynamic lessons learned and adheres to distinct brand voices.
    """

    async def generate_variations(
        self,
        brief: ContentBrief
    ) -> List[GeneratedVariation]:
        brand_clean = brief.brand.lower()
        platform_clean = brief.platform.lower()

        persona = BRAND_PERSONAS.get(brand_clean, BRAND_PERSONAS["jade"])
        plat_spec = PLATFORM_SPECS.get(platform_clean, PLATFORM_SPECS["linkedin"])

        # Fetch active lessons dynamically from database if not supplied
        active_lessons = brief.context_lessons or lessons_service.get_relevant_lessons_for_prompt(brand_clean, platform_clean)
        lessons_context = "\n".join([f"- {l}" for l in active_lessons]) if active_lessons else "None recorded."

        # Fetch relevant research context dynamically from database
        from app.services.research_service import research_service
        research_context = research_service.get_relevant_research_context(brand_clean, brief.topic)
        research_text = "\n".join([f"- {r}" for r in research_context]) if research_context else "General market opportunity."

        variations: List[GeneratedVariation] = []

        # If format is video/reel, invoke structured media pipeline
        if platform_clean in ["reel", "video"]:
            script = await media_service.generate_video_script(
                brand=brand_clean,
                topic=brief.topic,
                platform=platform_clean,
                language=brief.language,
                target_audience=brief.target_persona,
                active_lessons=active_lessons,
                research_context=research_text
            )
            # Format as variation A & B
            hook_text = f"\nHook: {script.hook}\n" if script.hook else ""
            var_a_text = (
                f"🎬 [VIDEO SCRIPT - Emotional & Trust Hook - {script.target_duration_seconds}s]\n"
                f"Title: {script.title or script.concept}\n"
                f"Concept: {script.concept}{hook_text}"
                f"Tone: {script.voiceover_tone}\n\n"
                + "\n\n".join([f"Scene {s.scene_number} ({s.duration_seconds}s):\nVisual: {s.visual_description}\nVO: \"{s.voiceover}\"\nOn-Screen: [{s.onscreen_text}]" for s in script.scenes])
                + f"\n\nCTA: {script.cta}\n\n{script.disclaimer}"
            )
            variations.append(
                GeneratedVariation(
                    variation_label="A",
                    content_text=var_a_text,
                    headline=f"Video Storyboard: {script.concept}",
                    hashtags=[f"#{brand_clean}", "#insurance", "#riskprotection"],
                    cta=script.cta,
                    media_prompt=f"Cinematic 4K storyboard for {brand_clean}: {brief.topic}"
                )
            )

            var_b_text = (
                f"📊 [VIDEO SCRIPT - Data & ROI Angle - 45s]\n"
                f"Concept: Financial Loss Analysis in {brief.topic}\n"
                f"Tone: Data-driven, authoritative\n\n"
                f"Scene 1 (10s):\nVisual: Dynamic infographics displaying average claim gap under standard sub-limits.\nVO: \"Standard insurance pays out less than 30% of true appraisal value for unlisted assets.\"\nOn-Screen: [The 70% Under-Insurance Exposure]\n\n"
                f"Scene 2 (15s):\nVisual: Side-by-side ledger comparing statutory caps vs {brand_clean.title()} agreed-value payout.\nVO: \"With {brand_clean.title()}, our agreed valuation locks in full appraisal value with zero deductible on certified items.\"\nOn-Screen: [Agreed Valuation Locks 100% Value]\n\n"
                f"Scene 3 (12s):\nVisual: Rapid claim settlement check cleared in 24 hours on mobile dashboard.\nVO: \"Protect your capital and prevent catastrophic balance sheet loss.\"\nOn-Screen: [Dedicated Claims Advisory]\n\n"
                f"Scene 4 (8s):\nVisual: Clean logo card with authorized broker badge.\nVO: \"Get your 2-minute private evaluation today.\"\nOn-Screen: [{persona['title']} | Inquire Today]\n\n"
                f"CTA: {brief.cta or 'Link in bio'}\n\n{persona['disclaimer']}"
            )
            variations.append(
                GeneratedVariation(
                    variation_label="B",
                    content_text=var_b_text,
                    headline=f"Data & ROI Breakdown: {brief.topic}",
                    hashtags=[f"#{brand_clean}", "#riskmanagement", "#assetprotection"],
                    cta=brief.cta or "Link in bio",
                    media_prompt=f"Infographic-driven video reel for {brand_clean}: {brief.topic}"
                )
            )
            return variations

        # Standard Text Variations (A: Emotional/Trust, B: Data/ROI)
        angles = [
            ("A", "Emotional, peace of mind, prestige, and trust-oriented"),
            ("B", "Data-driven, financial risk mitigation, sub-limit analysis, and ROI-oriented")
        ]

        lang_clean = (brief.language or "en").lower().strip()
        from app.services.localization_service import LANGUAGE_PROMPTS, localization_service
        lang_meta = LANGUAGE_PROMPTS.get(lang_clean, {"name": "English", "guidance": "Standard Singapore / International English with clear professional tone."})

        lang_directive = ""
        if lang_clean != "en":
            lang_directive = (
                f"TARGET REGIONAL LANGUAGE: {lang_meta['name']}\n"
                f"LOCALIZATION & REGULATORY GUIDELINES: {lang_meta['guidance']}\n"
                f"IMPORTANT: Write the entire post, headline, and call-to-action in {lang_meta['name']} using compliant regional insurance terms.\n\n"
            )

        for label, angle_desc in angles:
            prompt = (
                f"Draft marketing copy for brand '{brand_clean}' on platform '{platform_clean}'.\n"
                f"Variation: {label} ({angle_desc})\n"
                f"Topic: {brief.topic}\n"
                f"{lang_directive}"
                f"Key Benefits: {', '.join(brief.key_benefits) if brief.key_benefits else 'Comprehensive bespoke coverage'}\n"
                f"Target Persona: {brief.target_persona or 'High-value client / Specialist director'}\n"
                f"Brand Voice Directives:\n{persona['voice_directives']}\n\n"
                f"RELEVANT COMPETITOR & MARKET RESEARCH:\n{research_text}\n\n"
                f"LESSONS LEARNED FROM PAST HUMAN REVIEWS (STRICTLY ADHERE):\n{lessons_context}\n\n"
                f"MANDATORY DISCLAIMER TO INCLUDE AT END:\n{persona['disclaimer']}\n"
            )
            system_prompt = (
                f"You are the Lead Marketing Director for {persona['title']} fluent in {lang_meta['name']}. "
                f"Adhere strictly to {platform_clean} best practices ({plat_spec['style']})."
            )

            if llm_provider.is_live:
                generated_var: GeneratedVariation = llm_provider.generate_structured(
                    prompt=prompt,
                    schema=GeneratedVariation,
                    system_instruction=system_prompt
                )
                generated_var.variation_label = label
                if persona["disclaimer"] not in generated_var.content_text and "terms" not in generated_var.content_text.lower():
                    generated_var.content_text = f"{generated_var.content_text}\n\n{persona['disclaimer']}"
                variations.append(generated_var)
            else:
                # Deterministic high-quality fallback copy
                fallback_var = self._generate_deterministic_copy(
                    label=label,
                    brand=brand_clean,
                    platform=platform_clean,
                    topic=brief.topic,
                    persona=persona,
                    plat_spec=plat_spec
                )
                if lang_clean != "en":
                    fallback_var.content_text = localization_service._get_deterministic_localized_copy(
                        fallback_var.content_text, lang_clean, brand_clean
                    )
                variations.append(fallback_var)

        return variations

    def _generate_deterministic_copy(
        self,
        label: str,
        brand: str,
        platform: str,
        topic: str,
        persona: Dict[str, Any],
        plat_spec: Dict[str, Any]
    ) -> GeneratedVariation:
        """
        Deterministic, realistic copy adhering to compliance, brand voice, and format specs.
        """
        if brand == "jade":
            if label == "A": # Emotional/Trust
                headline = f"The True Worth of Heirlooms Beyond the Vault"
                body = (
                    f"Every rare diamond, vintage timepiece, and bespoke jewel carries more than monetary weight—it holds legacy, memory, and personal history.\n\n"
                    f"Yet, many collectors are unaware that standard homeowners policies impose severe sub-limits (frequently capped at $2,500) on unscheduled jewellery. In the event of travel loss or transit theft, standard insurers apply steep depreciation deductions.\n\n"
                    f"Jade by JA Assure was created specifically for high-net-worth connoisseurs. We provide agreed-value coverage based on certified independent appraisals, with worldwide protection across exhibitions, private travel, and home storage.\n\n"
                    f"Your legacy deserves unwavering protection.\n\n"
                    f"Discover bespoke coverage at the link in bio.\n\n"
                    f"{persona['disclaimer']}"
                )
            else: # Data-driven/ROI
                headline = f"Why Standard Home Policies Under-Insure Luxury Jewellery by up to 80%"
                body = (
                    f"A critical audit of private luxury collections across Southeast Asia reveals a startling statistic: over 75% of high-net-worth individuals are materially under-insured for rare watches and jewellery.\n\n"
                    f"Key Underwriting Discrepancies:\n"
                    f"• Sub-limits: General policies cap jewellery claims at $2,500 - $5,000.\n"
                    f"• Depreciation: Conventional claims deduct up to 40% for age and market fluctuation.\n"
                    f"• Travel Exclusions: Worldwide loss outside the domestic residence is often excluded.\n\n"
                    f"Jade by JA Assure solves this with:\n"
                    f"✓ 100% Agreed-Value reimbursement.\n"
                    f"✓ Certified gemologist appraisal validation.\n"
                    f"✓ Worldwide travel and transit coverage with zero deductible options.\n\n"
                    f"Review your portfolio limits today.\n\n"
                    f"{persona['disclaimer']}"
                )
            hashtags = ["#JadeInsurance", "#HauteHorlogerie", "#LuxuryJewellery", "#AssetProtection"]
        elif brand == "doctorshield":
            if label == "A": # Emotional/Trust
                headline = f"Preserving Your Practice, Reputation, and Peace of Mind"
                body = (
                    f"You have spent decades mastering clinical precision and building trust with your patients. But in an increasingly complex medico-legal climate, even an unsubstantiated claim can disrupt your practice.\n\n"
                    f"DoctorShield stands alongside private specialists. We provide dedicated medical professional indemnity with immediate access to seasoned panel malpractice defence counsel and retroactive coverage from day one.\n\n"
                    f"Focus on clinical excellence. Let DoctorShield protect your career.\n\n"
                    f"Learn more at doctorshield.asia.\n\n"
                    f"{persona['disclaimer']}"
                )
            else: # Data-driven/ROI
                headline = f"Managing Medico-Legal Risk in Private Specialist Practice"
                body = (
                    f"Recent regional healthcare data indicates legal defence costs for private specialist inquiries have increased by 22% over the past three years.\n\n"
                    f"Essential Pillars of DoctorShield Coverage:\n"
                    f"• Retroactive Protection: Continuous indemnity continuity without coverage lapses.\n"
                    f"• Rapid Legal Intervention: Immediate panel advocate assistance upon notice of inquiry.\n"
                    f"• Telemedicine Adaptation: Full coverage for cross-border virtual consultations under applicable regulations.\n\n"
                    f"Protect your clinical independence with predictable, tailored indemnity limits.\n\n"
                    f"Request a confidential consultation today.\n\n"
                    f"{persona['disclaimer']}"
                )
            hashtags = ["#DoctorShield", "#MedicalIndemnity", "#HealthcareLeadership", "#PracticeManagement"]
        else: # jaguartransit
            if label == "A": # Emotional/Trust
                headline = f"Uncompromising Security for High-Value Cargo in Transit"
                body = (
                    f"When moving irreplaceable valuables, fine art, or high-grade semiconductor consignments across regional hubs, peace of mind cannot be compromised.\n\n"
                    f"Jaguar Transit delivers vault-to-vault assurance with active GPS escort surveillance and vetted transit protocols. From departure gate to final destination, your precious cargo is shielded against the unexpected.\n\n"
                    f"Transport with confidence. Connect with our logistics desk.\n\n"
                    f"{persona['disclaimer']}"
                )
            else: # Data-driven/ROI
                headline = f"Mitigating Port Delay Exposure and Cargo Loss"
                body = (
                    f"Standard carrier liability (Warsaw & CMR conventions) limits payout to minimal statutory rates per kilogram—leaving 90%+ of high-value freight exposed to total loss during port congestions.\n\n"
                    f"The Jaguar Transit Solution:\n"
                    f"• Agreed-Value Transit: Full cargo invoice value covered without statutory sub-limits.\n"
                    f"• Extended Port Hold Rider: Coverage remains active during customs holds and transit delays.\n"
                    f"• Rapid Claims Turnaround: Dedicated claims settlement team for immediate liquidity.\n\n"
                    f"Eliminate transit balance sheet risk.\n\n"
                    f"{persona['disclaimer']}"
                )
            hashtags = ["#JaguarTransit", "#CargoInsurance", "#SupplyChainSecurity", "#Logistics"]

        if platform == "x":
            body = f"{headline}\n\n{body[:180]}...\n\n{persona['disclaimer'][:60]}"

        return GeneratedVariation(
            variation_label=label,
            content_text=body,
            headline=headline,
            hashtags=hashtags,
            cta="Learn more at our website.",
            media_prompt=f"Clean minimalist editorial visual for {brand}: {topic}"
        )

content_service = ContentService()
