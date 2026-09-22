import os
import json
import logging
import time
from typing import Optional, Dict, Any, Type, Union, List, get_origin, get_args
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger("ja_assure.llm")

class LLMProvider:
    """
    Unified LLM provider interface.
    Powered by Google Gemini (google.genai) when GEMINI_API_KEY is configured,
    or Groq API when GROQ_API_KEY is configured,
    and falls back to deterministic mock/demo responses when running in dev/demo mode
    without external API credentials.
    """

    # Prioritized Gemini models
    GEMINI_MODELS = [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-3-flash-preview",
        "gemini-pro-latest",
        "gemini-3.7-flash",
        "gemini-3.8-flash",
        "gemini-3.6-flash",
    ]

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.gemini_api_key = api_key or settings.GEMINI_API_KEY
        self.groq_api_key = settings.GROQ_API_KEY
        self.model_name = model_name or "gemini-3.5-flash-lite"
        self.provider_name = "Gemini" if self.gemini_api_key else ("Groq" if self.groq_api_key else "Mock")
        self._gemini_client = None
        self._groq_client = None
        self._initialize_client()

    def _initialize_client(self):
        if self.gemini_api_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.gemini_api_key)
                self.provider_name = "Gemini"
                logger.info("Google Gemini client initialized successfully with model pool: %s", self.GEMINI_MODELS)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self._gemini_client = None

        if self.groq_api_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.groq_api_key)
                self.model_name = "llama-3.3-70b-versatile" if settings.GROQ_MODEL in ("groq/compound", "", None) else settings.GROQ_MODEL
                if not self._gemini_client:
                    self.provider_name = "Groq"
                logger.info(f"Groq fallback client initialized with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")
                self._groq_client = None

        if not self._gemini_client and not self._groq_client:
            logger.info("No active LLM API keys provided; operating in demo/mock provider mode.")

    @property
    def is_live(self) -> bool:
        return self._gemini_client is not None or self._groq_client is not None

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Generate plain text response via Gemini (or Groq).
        """
        # 1. Try Gemini
        if self._gemini_client:
            full_prompt = f"System Instruction: {system_instruction}\n\nUser Prompt:\n{prompt}" if system_instruction else prompt
            for model_id in self.GEMINI_MODELS:
                try:
                    res = self._gemini_client.models.generate_content(
                        model=model_id,
                        contents=full_prompt
                    )
                    if res and res.text:
                        logger.info(f"Successfully generated text with Gemini model: {model_id}")
                        return res.text.strip()
                except Exception as e:
                    logger.warning(f"Gemini generation with {model_id} encountered issue: {e}. Trying next model...")
                    time.sleep(0.1)
                    continue

        # 2. Try Groq
        if self._groq_client:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            for attempt in range(2):
                try:
                    completion = self._groq_client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=0.7,
                        max_completion_tokens=2048
                    )
                    return completion.choices[0].message.content or ""
                except Exception as e:
                    if "429" in str(e) and attempt == 0:
                        time.sleep(2.5)
                        continue
                    logger.error(f"Groq API call failed: {e}")
                    break

        # Fallback / Demo mode output
        return f"[Demo Mode Output for prompt: {prompt[:80]}...]"

    def generate_structured(self, prompt: str, schema: Type[BaseModel], system_instruction: Optional[str] = None) -> BaseModel:
        """
        Generate structured output adhering to a Pydantic schema using Gemini or Groq JSON mode.
        """
        # 1. Try Gemini with native response_schema
        if self._gemini_client:
            full_prompt = (
                f"{system_instruction or 'You are an enterprise InsurTech AI marketing assistant.'}\n\n"
                f"{prompt}"
            )
            for model_id in self.GEMINI_MODELS:
                try:
                    res = self._gemini_client.models.generate_content(
                        model=model_id,
                        contents=full_prompt,
                        config={
                            "response_mime_type": "application/json",
                            "response_schema": schema
                        }
                    )
                    if res and res.text:
                        clean_json = res.text.strip()
                        if clean_json.startswith("```json"):
                            clean_json = clean_json[7:]
                        if clean_json.startswith("```"):
                            clean_json = clean_json[3:]
                        if clean_json.endswith("```"):
                            clean_json = clean_json[:-3]
                        clean_json = clean_json.strip()

                        data = json.loads(clean_json)
                        logger.info(f"Successfully generated structured output with Gemini model: {model_id}")
                        return schema.model_validate(data)
                except Exception as e:
                    logger.warning(f"Gemini structured generation with {model_id} failed: {e}. Trying next model...")
                    time.sleep(0.1)
                    continue

        # 2. Try Groq with JSON Mode
        if self._groq_client:
            schema_json = json.dumps(schema.model_json_schema(), indent=2)
            system_content = (
                f"{system_instruction or 'You are an enterprise InsurTech AI marketing assistant.'}\n\n"
                f"You MUST respond ONLY with valid JSON conforming to this JSON schema:\n{schema_json}"
            )
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]

            for attempt in range(2):
                try:
                    completion = self._groq_client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=0.3,
                        response_format={"type": "json_object"},
                        max_completion_tokens=2048
                    )

                    raw_text = completion.choices[0].message.content or "{}"
                    clean_json = raw_text.strip()
                    if clean_json.startswith("```json"):
                        clean_json = clean_json[7:]
                    if clean_json.startswith("```"):
                        clean_json = clean_json[3:]
                    if clean_json.endswith("```"):
                        clean_json = clean_json[:-3]
                    clean_json = clean_json.strip()

                    data = json.loads(clean_json)
                    return schema.model_validate(data)
                except Exception as e:
                    if "429" in str(e) and attempt == 0:
                        time.sleep(2.5)
                        continue
                    logger.error(f"Failed structured Groq generation: {e}")
                    break

        # In mock / demo mode, return default construct if available or basic mock
        return self._generate_fallback_mock(schema, prompt)

    def _generate_fallback_mock(self, schema: Type[BaseModel], prompt: str) -> BaseModel:
        """
        Produce a safe dummy object matching the Pydantic schema for seamless offline testing.
        """
        dummy_data: Dict[str, Any] = {}
        for name, field in schema.model_fields.items():
            dummy_data[name] = self._mock_value_for_annotation(field.annotation, name, prompt)

        try:
            return schema.model_validate(dummy_data)
        except Exception:
            return schema.model_construct(**dummy_data)

    def _mock_value_for_annotation(self, annotation: Any, name: str, prompt: str) -> Any:
        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin is Union:
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                return self._mock_value_for_annotation(non_none[0], name, prompt)
            return None

        if origin in (list, set, tuple) or annotation in (list, set, tuple):
            item_type = args[0] if args else None
            if isinstance(item_type, type) and issubclass(item_type, BaseModel):
                if item_type.__name__ == "VideoScene":
                    p_lower = prompt.lower()
                    if "doctorshield" in p_lower:
                        return [
                            item_type(scene_number=1, duration_seconds=10, visual_description="A specialist surgeon in clinical theater reviewing patient records with focused precision.", voiceover="In complex clinical practice, unexpected claims can emerge years after treatment.", onscreen_text="Preserving Clinical Careers | Defensible Peace of Mind", transition="Smooth Crossfade", compliance_disclaimer="*DoctorShield is underwritten by licensed partner insurers.*"),
                            item_type(scene_number=2, duration_seconds=15, visual_description="Senior medico-legal defense counsel analyzing statutory documentation at private advisory desk.", voiceover="DoctorShield connects healthcare practitioners with dedicated panel attorneys and retroactive liability protection.", onscreen_text="Statutory Inquiries & Disciplinary Defense Coverage", transition="Cut", compliance_disclaimer="*DoctorShield provides indemnity support for licensed practitioners.*"),
                            item_type(scene_number=3, duration_seconds=12, visual_description="Reassuring consultation between experienced specialist physician and hospital administrator.", voiceover="Protect your medical registration, personal reputation, and peace of mind.", onscreen_text="Comprehensive Medical Indemnity | Up to $10M Policy Limits", transition="Fade to Black", compliance_disclaimer="*Terms, conditions, and underwriting limits apply.*")
                        ]
                    elif "jaguartransit" in p_lower:
                        return [
                            item_type(scene_number=1, duration_seconds=10, visual_description="High-security armored transport convoy departing bonded customs facility under satellite escort.", voiceover="High-value freight faces rising port congestion and transit vulnerabilities across Southeast Asia.", onscreen_text="Chain of Custody | Real-Time Active Monitoring", transition="Whip Pan", compliance_disclaimer="*Jaguar Transit is underwritten by licensed partner insurers.*"),
                            item_type(scene_number=2, duration_seconds=15, visual_description="Logistics command center tracking live GPS sensor telemetry for precious diamond cargo.", voiceover="Jaguar Transit delivers vault-grade custody protocols and active GPS escort riders from port to private vault.", onscreen_text="Vault-Grade Custody | Port-to-Port Transit Certainty", transition="Cut", compliance_disclaimer="*Full policy terms apply to bonded routes.*"),
                            item_type(scene_number=3, duration_seconds=12, visual_description="Secure delivery confirmation stamped inside certified high-security facility.", voiceover="Eliminate supply chain balance sheet risk with tailored 24-hour claim resolution.", onscreen_text="Zero-Deductible High-Risk Transit Protection", transition="Fade to Black", compliance_disclaimer="*Terms and conditions apply.*")
                        ]
                    else:
                        return [
                            item_type(scene_number=1, duration_seconds=10, visual_description="Macro cinematic shot of a master gemologist examining a flawless diamond with a magnifying loupe in private showroom.", voiceover="Your jewellery collection holds generational legacy and irreplaceable memories.", onscreen_text="The True Worth of Heirlooms | Agreed-Value Protection", transition="Slow Dissolve", compliance_disclaimer="*Jade is underwritten by licensed partner insurers.*"),
                            item_type(scene_number=2, duration_seconds=15, visual_description="Close-up of a luxury mechanical tourbillon timepiece in a secure velvet vault case.", voiceover="Standard homeowner insurance policies cap unscheduled jewellery at $2,500 with heavy depreciation.", onscreen_text="Sub-Limits vs 100% Agreed-Value Reimbursement", transition="Cut", compliance_disclaimer="*Certified appraisal validation applies.*"),
                            item_type(scene_number=3, duration_seconds=12, visual_description="Discreet collector wearing haute horlogerie timepiece boarding private aviation charter.", voiceover="Jade by JA Assure provides agreed-value protection with worldwide travel and transit coverage.", onscreen_text="Worldwide Protection | Zero Deductible Options", transition="Fade to Black", compliance_disclaimer="*Terms, conditions, and underwriting limits apply.*")
                        ]
    def _detect_target_brand(self, prompt: str) -> str:
        p = prompt.lower()
        if "brand 'jade'" in p or "brand: jade" in p or "for brand 'jade'" in p or "jade (luxury" in p:
            return "jade"
        if "brand 'doctorshield'" in p or "brand: doctorshield" in p or "for brand 'doctorshield'" in p or "doctorshield (medical" in p:
            return "doctorshield"
        if "brand 'jaguartransit'" in p or "brand: jaguartransit" in p or "for brand 'jaguartransit'" in p or "jaguar transit" in p:
            return "jaguartransit"
        if "jewellery" in p or "jewelry" in p or "gemologist" in p or "horlogerie" in p or "heirloom" in p:
            return "jade"
        if "medical" in p or "doctor" in p or "surgeon" in p or "clinical" in p or "medico-legal" in p:
            return "doctorshield"
        if "cargo" in p or "freight" in p or "transit" in p or "logistics" in p:
            return "jaguartransit"
        return "jade"

    def _mock_value_for_annotation(self, annotation: Any, name: str, prompt: str) -> Any:
        origin = get_origin(annotation)
        args = get_args(annotation)
        target_brand = self._detect_target_brand(prompt)
        p_lower = prompt.lower()
        is_var_b = "variation: b" in p_lower or "variation b" in p_lower

        if origin is Union:
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                return self._mock_value_for_annotation(non_none[0], name, prompt)
            return None

        if origin in (list, set, tuple) or annotation in (list, set, tuple):
            item_type = args[0] if args else None
            if isinstance(item_type, type) and issubclass(item_type, BaseModel):
                if item_type.__name__ == "VideoScene":
                    if target_brand == "doctorshield":
                        return [
                            item_type(scene_number=1, duration_seconds=10, visual_description="A specialist surgeon in clinical theater reviewing patient records with focused precision.", voiceover="In complex clinical practice, unexpected claims can emerge years after treatment.", onscreen_text="Preserving Clinical Careers | Defensible Peace of Mind", transition="Smooth Crossfade", compliance_disclaimer="*DoctorShield is underwritten by licensed partner insurers.*"),
                            item_type(scene_number=2, duration_seconds=15, visual_description="Senior medico-legal defense counsel analyzing statutory documentation at private advisory desk.", voiceover="DoctorShield connects healthcare practitioners with dedicated panel attorneys and retroactive liability protection.", onscreen_text="Statutory Inquiries & Disciplinary Defense Coverage", transition="Cut", compliance_disclaimer="*DoctorShield provides indemnity support for licensed practitioners.*"),
                            item_type(scene_number=3, duration_seconds=12, visual_description="Reassuring consultation between experienced specialist physician and hospital administrator.", voiceover="Protect your medical registration, personal reputation, and peace of mind.", onscreen_text="Comprehensive Medical Indemnity | Up to $10M Policy Limits", transition="Fade to Black", compliance_disclaimer="*Terms, conditions, and underwriting limits apply.*")
                        ]
                    elif target_brand == "jaguartransit":
                        return [
                            item_type(scene_number=1, duration_seconds=10, visual_description="High-security armored transport convoy departing bonded customs facility under satellite escort.", voiceover="High-value freight faces rising port congestion and transit vulnerabilities across Southeast Asia.", onscreen_text="Chain of Custody | Real-Time Active Monitoring", transition="Whip Pan", compliance_disclaimer="*Jaguar Transit is underwritten by licensed partner insurers.*"),
                            item_type(scene_number=2, duration_seconds=15, visual_description="Logistics command center tracking live GPS sensor telemetry for precious diamond cargo.", voiceover="Jaguar Transit delivers vault-grade custody protocols and active GPS escort riders from port to private vault.", onscreen_text="Vault-Grade Custody | Port-to-Port Transit Certainty", transition="Cut", compliance_disclaimer="*Full policy terms apply to bonded routes.*"),
                            item_type(scene_number=3, duration_seconds=12, visual_description="Secure delivery confirmation stamped inside certified high-security facility.", voiceover="Eliminate supply chain balance sheet risk with tailored 24-hour claim resolution.", onscreen_text="Zero-Deductible High-Risk Transit Protection", transition="Fade to Black", compliance_disclaimer="*Terms and conditions apply.*")
                        ]
                    else:
                        return [
                            item_type(scene_number=1, duration_seconds=10, visual_description="Macro cinematic shot of a master gemologist examining a flawless diamond with a magnifying loupe in private showroom.", voiceover="Your jewellery collection holds generational legacy and irreplaceable memories.", onscreen_text="The True Worth of Heirlooms | Agreed-Value Protection", transition="Slow Dissolve", compliance_disclaimer="*Jade is underwritten by licensed partner insurers.*"),
                            item_type(scene_number=2, duration_seconds=15, visual_description="Close-up of a luxury mechanical tourbillon timepiece in a secure velvet vault case.", voiceover="Standard homeowner insurance policies cap unscheduled jewellery at $2,500 with heavy depreciation.", onscreen_text="Sub-Limits vs 100% Agreed-Value Reimbursement", transition="Cut", compliance_disclaimer="*Certified appraisal validation applies.*"),
                            item_type(scene_number=3, duration_seconds=12, visual_description="Discreet collector wearing haute horlogerie timepiece boarding private aviation charter.", voiceover="Jade by JA Assure provides agreed-value protection with worldwide travel and transit coverage.", onscreen_text="Worldwide Protection | Zero Deductible Options", transition="Fade to Black", compliance_disclaimer="*Terms, conditions, and underwriting limits apply.*")
                        ]
                return [self._build_mock_instance(item_type, prompt)]
            if name == "hashtags":
                if target_brand == "doctorshield":
                    return ["#DoctorShield", "#MedicalIndemnity", "#MedicoLegal", "#HealthcareLaw"]
                if target_brand == "jaguartransit":
                    return ["#JaguarTransit", "#CargoInsurance", "#SupplyChainSecurity", "#Logistics"]
                return ["#JadeInsurance", "#HauteHorlogerie", "#LuxuryJewellery", "#AssetProtection"]
            if name == "pain_points":
                return ["Sub-limit claim caps on unlisted items", "Depreciation deductions up to 40%", "Travel exclusions outside domestic residence"]
            if name == "recommended_angles":
                return ["Agreed-Value Valuation vs Statutory Depreciation", "Certified Gemologist Appraisal Integrity", "Worldwide Exhibition and Transit Security"]
            if name == "sources":
                return ["Monetary Authority of Singapore Guidelines", "JA Assure High-Net-Worth Market Survey", "Southeast Asia Luxury Risk Audit 2026"]
            return ["Agreed-value underwriting", "Certified gemologist appraisal", "Worldwide transit custody"]

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return self._build_mock_instance(annotation, prompt)

        if origin is dict or annotation is dict:
            return {}
        if annotation is bool:
            return True
        if annotation is int:
            return 1
        if annotation is float:
            return 95.0
        if annotation is str:
            if name == "variation_label":
                return "B" if is_var_b else "A"
            if name == "concept":
                if target_brand == "doctorshield":
                    return "Medico-Legal Defense and Career Preservation for Private Specialists"
                if target_brand == "jaguartransit":
                    return "Zero-Deductible Vault-Grade Custody for High-Value Multimodal Cargo"
                return "Preserving Generational Heirlooms Beyond Conventional Policy Sub-Limits"
            if name == "hook":
                if target_brand == "doctorshield":
                    return "Are your clinical indemnity limits sufficient for retroactive disciplinary defense?"
                if target_brand == "jaguartransit":
                    return "Is your precious cargo exposed to port congestion and transit theft?"
                return "Did you know that 75% of luxury jewellery is under-insured by standard policies?"
            if name == "title":
                if target_brand == "doctorshield":
                    return "DoctorShield Specialist Indemnity Architecture"
                if target_brand == "jaguartransit":
                    return "Jaguar Transit High-Security Cargo Protection"
                return "Jade Agreed-Value Jewellery Insurance Storyboard"
            if name == "visual_description":
                return "Cinematic macro shot of a master gemologist examining a bespoke emerald cut diamond under studio lighting."
            if name == "voiceover":
                return "Jade by JA Assure provides agreed-value protection with certified appraisal validation."
            if name == "onscreen_text":
                return "Agreed-Value Protection | Worldwide Transit Coverage"
            if name == "transition":
                return "Smooth Dissolve"
            if name == "compliance_disclaimer" or name == "disclaimer":
                if target_brand == "doctorshield":
                    return "*DoctorShield is a medical indemnity policy underwritten by licensed partner insurers. Terms and conditions apply.*"
                if target_brand == "jaguartransit":
                    return "*Jaguar Transit cargo insurance is underwritten by licensed partner insurers. Terms and conditions apply.*"
                return "*Terms, conditions, and underwriting limits apply. Jade is underwritten by licensed partner insurers.*"
            if name == "headline":
                if target_brand == "doctorshield":
                    return "Managing Medico-Legal Risk in Private Specialist Practice" if is_var_b else "Preserving Your Medical Practice, Reputation, and Peace of Mind"
                if target_brand == "jaguartransit":
                    return "Mitigating Port Delay Exposure and Cargo Loss" if is_var_b else "Securing High-Value Cargo with Active GPS and Vault-Grade Custody"
                return "Why Standard Home Policies Under-Insure Luxury Jewellery by up to 80%" if is_var_b else "The True Worth of Heirlooms Beyond the Vault"
            if name == "content_text":
                if target_brand == "doctorshield":
                    if is_var_b:
                        return (
                            "Recent regional healthcare data indicates legal defence costs for private specialist inquiries have increased by 22% over the past three years.\n\n"
                            "Essential Pillars of DoctorShield Coverage:\n"
                            "• Retroactive Protection: Continuous indemnity continuity without coverage lapses.\n"
                            "• Rapid Legal Intervention: Immediate panel advocate assistance upon notice of inquiry.\n"
                            "• Telemedicine Adaptation: Full coverage for cross-border virtual consultations.\n\n"
                            "Protect your clinical independence with predictable indemnity limits.\n\n"
                            "*DoctorShield is underwritten by licensed partner insurers. Terms and conditions apply.*"
                        )
                    return (
                        "You have spent decades mastering clinical precision and building trust with your patients. In private clinical practice, career longevity depends on robust medico-legal protection and retroactive liability defense.\n\n"
                        "DoctorShield connects you with specialist healthcare advocates for comprehensive legal defense.\n\n"
                        "*DoctorShield is underwritten by licensed partner insurers. Terms and conditions apply.*"
                    )
                if target_brand == "jaguartransit":
                    if is_var_b:
                        return (
                            "Standard carrier liability (Warsaw & CMR conventions) limits payout to minimal statutory rates per kilogram—leaving 90%+ of high-value freight exposed to total loss during port congestions.\n\n"
                            "The Jaguar Transit Solution:\n"
                            "• Agreed-Value Transit: Full cargo invoice value covered without statutory sub-limits.\n"
                            "• Extended Port Hold Rider: Active protection during customs holds and transit delays.\n"
                            "• Rapid Claims Turnaround: Dedicated settlement desk for immediate liquidity.\n\n"
                            "*Jaguar Transit is underwritten by licensed partner insurers. Terms and conditions apply.*"
                        )
                    return (
                        "Global multimodal supply chains require ironclad security and balance sheet certainty against transit disruptions.\n\n"
                        "Jaguar Transit provides vault-grade custody and continuous real-time cargo tracking.\n\n"
                        "*Jaguar Transit is underwritten by licensed partner insurers. Terms and conditions apply.*"
                    )
                if is_var_b:
                    return (
                        "A critical audit of private luxury collections across Southeast Asia reveals a startling statistic: over 75% of high-net-worth individuals are materially under-insured for rare watches and jewellery.\n\n"
                        "Key Underwriting Discrepancies:\n"
                        "• Sub-limits: General policies cap jewellery claims at $2,500 - $5,000.\n"
                        "• Depreciation: Conventional claims deduct up to 40% for age and market fluctuation.\n"
                        "• Travel Exclusions: Worldwide loss outside the domestic residence is often excluded.\n\n"
                        "Jade by JA Assure solves this with:\n"
                        "✓ 100% Agreed-Value reimbursement.\n"
                        "✓ Certified gemologist appraisal validation.\n"
                        "✓ Worldwide travel and transit coverage with zero deductible options.\n\n"
                        "Review your portfolio limits today.\n\n"
                        "*Terms, conditions, and underwriting limits apply. Jade is underwritten by licensed partner insurers.*"
                    )
                return (
                    "Every rare diamond, vintage timepiece, and bespoke jewel carries more than monetary weight—it holds legacy, memory, and personal history.\n\n"
                    "Yet, standard homeowner policies cap unscheduled jewellery claims at $2,500 with steep depreciation. Jade by JA Assure provides agreed-value coverage based on certified independent appraisals, with worldwide protection across exhibitions, private travel, and home storage.\n\n"
                    "Your legacy deserves unwavering protection.\n\n"
                    "*Terms, conditions, and underwriting limits apply. Jade is underwritten by licensed partner insurers.*"
                )
            if name == "cta":
                if target_brand == "doctorshield":
                    return "Request a confidential advisory review at ja-assure.com/doctorshield"
                if target_brand == "jaguartransit":
                    return "Speak with our logistics risk desk at ja-assure.com/jaguartransit"
                return "Consult our underwriting team today at ja-assure.com/jade"
            return f"Strategic Asset Protection Brief for {name.replace('_', ' ').title()}"
        return None

    def _build_mock_instance(self, schema: Type[BaseModel], prompt: str) -> BaseModel:
        """Recursively builds one valid dummy instance of a nested Pydantic model."""
        dummy_data = {
            name: self._mock_value_for_annotation(field.annotation, name, prompt)
            for name, field in schema.model_fields.items()
        }
        try:
            return schema.model_validate(dummy_data)
        except Exception:
            return schema.model_construct(**dummy_data)
        except Exception:
            return schema.model_construct(**dummy_data)

# Singleton provider instance
llm_provider = LLMProvider()
