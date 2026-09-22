import logging
from typing import Dict, Any, List, Optional
from app.schemas.agent_contracts import VideoScript, VideoScene
from app.services.llm_provider import llm_provider

logger = logging.getLogger("ja_assure.media")

class MediaService:
    """
    Video/Reels Storyboard and Visual Pipeline Service.
    Produces 30-60 second structured AI storyboards with scene-by-scene visual cues,
    voiceover text, on-screen typography, transitions, and mandatory compliance disclaimers.
    Uses Gemini structured output when live, with domain-accurate deterministic fallback.
    """

    async def generate_video_script(
        self,
        brand: str,
        topic: str,
        target_duration: int = 45,
        concept_notes: Optional[str] = None,
        platform: str = "reel",
        language: str = "en",
        target_audience: Optional[str] = None,
        research_context: Optional[str] = None,
        compliance_context: Optional[str] = None,
        active_lessons: Optional[List[str]] = None
    ) -> VideoScript:
        brand_clean = brand.lower()
        platform_clean = platform.lower()
        lang_clean = language.lower()

        # Import brand personas safely to avoid circular import
        from app.services.content_service import BRAND_PERSONAS
        persona = BRAND_PERSONAS.get(brand_clean, BRAND_PERSONAS.get("jade", {
            "title": f"JA Assure {brand_clean.title()}",
            "tone": "Professional, authoritative, reassuring",
            "voice_directives": "Highlight specialized underwriting and protection.",
            "disclaimer": "*Terms, conditions, and underwriting limits apply. Underwritten by licensed partner insurers.*"
        }))

        # Retrieve active lessons if not provided
        if active_lessons is None:
            from app.services.lessons_service import lessons_service
            active_lessons = lessons_service.get_relevant_lessons_for_prompt(brand_clean, platform_clean)

        # Retrieve research context if not provided
        if research_context is None:
            try:
                from app.services.research_service import research_service
                cues = research_service.get_relevant_research_context(brand_clean, topic)
                research_context = "\n".join(f"- {c}" for c in cues) if cues else None
            except Exception:
                research_context = None

        # 1. LIVE GEMINI GENERATION
        if llm_provider.is_live:
            try:
                lessons_formatted = "\n".join(f"- {l}" for l in active_lessons) if active_lessons else "None recorded."
                research_formatted = f"Market & Competitor Insights:\n{research_context}\n\n" if research_context else ""
                audience_str = target_audience or "High-net-worth collectors, practice owners, or corporate logistics directors"

                prompt = (
                    f"Create an engaging, highly compliant, high-converting short-form video/Reel storyboard for {persona['title']}.\n\n"
                    f"CAMPAIGN BRIEF:\n"
                    f"- Topic: {topic}\n"
                    f"- Target Platform: {platform_clean} (format for dynamic vertical video storytelling)\n"
                    f"- Language: {lang_clean} (Write voiceover, onscreen_text, and hook in {lang_clean}!)\n"
                    f"- Target Audience: {audience_str}\n"
                    f"- Target Total Duration: {target_duration} seconds (create 4-6 scenes summing to approximately {target_duration}s)\n\n"
                    f"BRAND VOICE & TONAL GUIDELINES:\n"
                    f"- Tone: {persona['tone']}\n"
                    f"- Directives: {persona['voice_directives']}\n\n"
                    f"{research_formatted}"
                    f"ACTIVE LESSONS LEARNED FROM HUMAN REVIEWERS (STRICTLY ADHERE):\n"
                    f"{lessons_formatted}\n\n"
                    f"REGULATORY COMPLIANCE DIRECTIVES (MANDATORY):\n"
                    f"- Prohibit absolute promises ('100% guaranteed', 'zero risk', 'never denied', 'cheapest rates').\n"
                    f"- Mandatory Final Intermediary Disclaimer: '{persona['disclaimer']}'\n"
                    f"- For DoctorShield: Never provide patient medical advice, diagnosis, or clinical outcome guarantees.\n"
                    + (f"- Additional Compliance Context: {compliance_context}\n" if compliance_context else "") +
                    f"\nSTORYBOARD REQUIREMENTS:\n"
                    f"- Set 'title' and an attention-grabbing opening 'hook'.\n"
                    f"- Generate 4 to 6 scenes.\n"
                    f"- Each scene MUST contain: scene_number, duration_seconds, visual_description, voiceover, onscreen_text, transition (e.g. 'Match Cut', 'Whip Pan', 'Dissolve', 'J-Cut'), and compliance_disclaimer if needed.\n"
                    f"- Compelling CTA and regulatory disclaimer."
                )

                system_instruction = (
                    f"You are the Executive Creative Video Director and Compliance Officer for JA Assure ({persona['title']}). "
                    f"Generate structured video scripts with cinematic visual cues and compliant copy."
                )

                script: VideoScript = llm_provider.generate_structured(
                    prompt=prompt,
                    schema=VideoScript,
                    system_instruction=system_instruction
                )

                # Ensure core fields are populated
                script.brand = brand_clean
                script.target_platform = platform_clean
                script.language = lang_clean
                script.media_status = "ai_storyboard_generated"
                if not script.scenes or not isinstance(script.scenes[0], VideoScene):
                    raise ValueError("Structured LLM output did not contain valid VideoScene instances. Triggering deterministic fallback.")
                if not script.title:
                    script.title = f"AI Storyboard: {topic[:50]}"
                if not script.concept:
                    script.concept = script.title
                if not script.cta:
                    script.cta = f"Consult JA Assure {persona['title']} for bespoke underwriting."
                if not script.hook and script.scenes and hasattr(script.scenes[0], 'onscreen_text'):
                    script.hook = script.scenes[0].onscreen_text
                if not script.disclaimer:
                    script.disclaimer = persona["disclaimer"]
                if script.scenes and hasattr(script.scenes[0], 'duration_seconds'):
                    script.target_duration_seconds = sum(getattr(s, 'duration_seconds', 10) for s in script.scenes)

                logger.info(f"Successfully generated AI video storyboard with Gemini for {brand_clean}: '{script.title}'")
                return script
            except Exception as e:
                logger.error(f"Gemini video storyboard generation failed: {e}. Using deterministic fallback.")

        # 2. DETERMINISTIC FALLBACK GENERATION (Offline / Resilient)
        return self._generate_deterministic_video_script(
            brand=brand_clean,
            topic=topic,
            target_duration=target_duration,
            platform=platform_clean,
            language=lang_clean,
            persona=persona,
            concept_notes=concept_notes
        )

    def _generate_deterministic_video_script(
        self,
        brand: str,
        topic: str,
        target_duration: int,
        platform: str,
        language: str,
        persona: Dict[str, Any],
        concept_notes: Optional[str] = None
    ) -> VideoScript:
        if brand == "jade":
            title = f"Safeguarding Heirlooms: {topic}"
            concept = concept_notes or f"The Hidden Sub-Limits in Standard Home Insurance vs Agreed-Value Jade Protection"
            hook = "Are your rare watches and heirloom jewellery actually insured for what they're worth?"
            scenes = [
                VideoScene(
                    scene_number=1,
                    duration_seconds=10,
                    visual_description="Cinematic macro shot of a diamond solitaire ring alongside a luxury Swiss timepiece on an emerald velvet tray.",
                    voiceover="Most luxury collectors assume their heirlooms are completely protected under home insurance. But have you checked your unscheduled jewellery sub-limit?",
                    onscreen_text="Did You Know? Standard home policies cap jewellery at $2,500.",
                    transition="Slow Push-In to Macro",
                    compliance_disclaimer=None
                ),
                VideoScene(
                    scene_number=2,
                    duration_seconds=12,
                    visual_description="Split screen: Left side shows a generic rejected insurance claim notice; Right side shows a certified gemologist appraisal with a Jade seal.",
                    voiceover=f"When protecting pieces valued in {topic}, standard insurers apply steep depreciation deductions. Jade by JA Assure pays 100% of agreed appraisal value.",
                    onscreen_text="Agreed-Value Valuation vs General Depreciation",
                    transition="Whip Pan Transition",
                    compliance_disclaimer="Subject to certified appraisal underwriting."
                ),
                VideoScene(
                    scene_number=3,
                    duration_seconds=13,
                    visual_description="Elegant collector stepping out of a private lounge wearing the watch, subtle glowing shield animation indicating active worldwide coverage.",
                    voiceover="From international art fairs to private travel, your collection is protected globally with zero deductible on certified pieces.",
                    onscreen_text="Worldwide Transit & Travel • Zero Deductible Available",
                    transition="Smooth Match Cut",
                    compliance_disclaimer=None
                ),
                VideoScene(
                    scene_number=4,
                    duration_seconds=10,
                    visual_description="Minimalist dark slate background displaying Jade by JA Assure gold typography and authorized broker credentials.",
                    voiceover="Protect what cannot be replaced. Get your confidential valuation review at the link in bio.",
                    onscreen_text="Jade by JA Assure | Protect Your Legacy | Link in Bio",
                    transition="Fade to End Card",
                    compliance_disclaimer=persona["disclaimer"]
                )
            ]
        elif brand == "doctorshield":
            title = f"Defending Clinical Independence: {topic}"
            concept = concept_notes or f"Navigating Medico-Legal Liabilities and Telemedicine Risks for Private Specialists"
            hook = "In modern healthcare, a single inquiry can disrupt decades of clinical practice."
            scenes = [
                VideoScene(
                    scene_number=1,
                    duration_seconds=10,
                    visual_description="Specialist physician reviewing patient records on a tablet in a modern private medical clinic.",
                    voiceover="Medicine moves at the speed of innovation. But virtual consultations and complex aesthetic procedures introduce unprecedented liability exposure.",
                    onscreen_text="Telehealth & Aesthetics Expanding: Are Your Indemnity Limits Covered?",
                    transition="Slow Dolly In",
                    compliance_disclaimer=None
                ),
                VideoScene(
                    scene_number=2,
                    duration_seconds=12,
                    visual_description="Gavel graphic transitioning smoothly into legal counsel defence documents with malpractice timeline icons.",
                    voiceover=f"Addressing {topic} requires specialized legal defense counsel from day one, not generic claims handlers.",
                    onscreen_text="Dedicated Panel Malpractice Counsel + Retroactive Cover",
                    transition="Clean Slide Left",
                    compliance_disclaimer="Indemnity cover only; does not provide clinical diagnostic guidance."
                ),
                VideoScene(
                    scene_number=3,
                    duration_seconds=13,
                    visual_description="Doctor warmly shaking hands with a patient, projecting calm clinical confidence.",
                    voiceover="DoctorShield stands alongside private specialists. Continuous retroactive cover and immediate advocate intervention mean you practice with complete peace of mind.",
                    onscreen_text="Practice with Certainty • Tailored for Private Specialists",
                    transition="Match Dissolve",
                    compliance_disclaimer=None
                ),
                VideoScene(
                    scene_number=4,
                    duration_seconds=10,
                    visual_description="DoctorShield logo in deep navy blue with registered intermediary broker badge.",
                    voiceover="Safeguard your medical practice and reputation. Inquire privately with DoctorShield.",
                    onscreen_text="DoctorShield | Medical Professional Indemnity | Inquire Privately",
                    transition="Fade to Navy",
                    compliance_disclaimer=persona["disclaimer"]
                )
            ]
        else: # jaguartransit
            title = f"Vault-Grade Cargo Security: {topic}"
            concept = concept_notes or f"Mitigating Port Delay Volatility and High-Value Freight Exposure"
            hook = "Standard cargo contracts limit liability to pennies per kilo. Who covers the gap?"
            scenes = [
                VideoScene(
                    scene_number=1,
                    duration_seconds=10,
                    visual_description="Time-lapse of port container gantries loading freight at dusk, digital tracking route overlay showing delay alerts.",
                    voiceover="Regional port congestion and customs holds can halt high-value consignments overnight. Standard marine policies exclude losses beyond 72 hours.",
                    onscreen_text="Port Delays Shouldn't Jeopardize High-Value Consignments.",
                    transition="Rapid Zoom to Map",
                    compliance_disclaimer=None
                ),
                VideoScene(
                    scene_number=2,
                    duration_seconds=12,
                    visual_description="Armoured courier van sealed with electronic GPS biometric lock passing airport bonded gates.",
                    voiceover=f"When transporting valuable assets in {topic}, Jaguar Transit delivers agreed-value vault protection from warehouse gate to final destination.",
                    onscreen_text="Agreed-Value Vault Transit vs Warsaw/CMR Statutory Caps",
                    transition="Whip Pan",
                    compliance_disclaimer=None
                ),
                VideoScene(
                    scene_number=3,
                    duration_seconds=13,
                    visual_description="Operations dashboard tracking live temperature and satellite GPS coordinates with green clearance ticks.",
                    voiceover="With active escort tracking and expedited claim settlement for transit losses, your balance sheet remains completely protected.",
                    onscreen_text="24/7 Active GPS Escort Tracking & Rapid Claims Dispatch",
                    transition="Clean Cut",
                    compliance_disclaimer=None
                ),
                VideoScene(
                    scene_number=4,
                    duration_seconds=10,
                    visual_description="Metallic Jaguar Transit shield emblem with secure cargo seal.",
                    voiceover="Secure your regional transit routes. Connect with the Jaguar Transit logistics underwriting desk.",
                    onscreen_text="Jaguar Transit | High-Value Valuables Cargo Insurance",
                    transition="Fade to Black",
                    compliance_disclaimer=persona["disclaimer"]
                )
            ]

        total_duration = sum(s.duration_seconds for s in scenes)

        return VideoScript(
            brand=brand,
            title=title,
            concept=concept,
            hook=hook,
            target_duration_seconds=total_duration,
            voiceover_tone=persona["tone"],
            target_platform=platform,
            target_audience=None,
            language=language,
            scenes=scenes,
            cta="Inquire at JA Assure today.",
            disclaimer=persona["disclaimer"],
            media_status="ai_storyboard_generated"
        )

media_service = MediaService()
