import os
import json
import logging
from typing import Optional, Dict, Any, Type, Union, get_origin, get_args
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger("ja_assure.llm")

class LLMProvider:
    """
    Unified LLM provider interface.
    Powered by Groq API when GROQ_API_KEY is configured,
    and falls back to deterministic mock/demo responses when running in dev/demo mode
    without external API credentials.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model_name = model_name or settings.GROQ_MODEL
        self.provider_name = "Groq"
        self._groq_client = None
        self._initialize_client()

    def _initialize_client(self):
        if self.api_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.api_key)
                logger.info(f"Groq client initialized with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}. Falling back to mock mode.")
                self._groq_client = None
        else:
            logger.info("No GROQ_API_KEY provided; operating in demo/mock provider mode.")

    @property
    def is_live(self) -> bool:
        return self._groq_client is not None

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Generate plain text response via Groq chat completions.
        """
        if self.is_live:
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
                        logger.warning("Groq rate limit encountered. Retrying in 2.5s...")
                        import time
                        time.sleep(2.5)
                        continue
                    logger.error(f"Groq API call failed: {e}. Fallback triggered.")
                    break

        # Fallback / Demo mode output
        return f"[Demo Mode Output for prompt: {prompt[:80]}...]"

    def generate_structured(self, prompt: str, schema: Type[BaseModel], system_instruction: Optional[str] = None) -> BaseModel:
        """
        Generate structured output adhering to a Pydantic schema using Groq JSON mode.
        """
        if self.is_live:
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
                    # Some models occasionally wrap the requested object in a
                    # single-element list instead of returning it bare, despite
                    # the schema (and prompt) asking for an object -- unwrap
                    # that one known shape rather than failing validation and
                    # discarding a genuinely good response.
                    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
                        data = data[0]
                    return schema.model_validate(data)
                except Exception as e:
                    if "429" in str(e) and attempt == 0:
                        logger.warning("Groq rate limit encountered. Retrying in 2.5s...")
                        import time
                        time.sleep(2.5)
                        continue
                    logger.error(f"Failed structured Groq generation: {e}. Falling back to schema mock.")
                    break

        # In mock / demo mode, return default construct if available or basic mock
        return self._generate_fallback_mock(schema, prompt)

    def _generate_fallback_mock(self, schema: Type[BaseModel], prompt: str) -> BaseModel:
        """
        Produce a safe dummy object matching the Pydantic schema for seamless offline testing.

        Type-introspects each field (get_origin/get_args) rather than string-matching the
        annotation, specifically so a List[SomeNestedModel] field (e.g. VideoScript.scenes:
        List[VideoScene]) gets a real, valid nested model instance -- not a bare string.
        The old string-matching version always produced `["Demo item 1"]` for ANY list
        field regardless of its item type, which fails schema validation for a list of
        models and previously fell through to model_construct() (which skips validation
        entirely), silently handing callers a list of strings where objects were expected.
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

        # Unwrap Optional[X] (== Union[X, None]) to X for picking a dummy value.
        if origin is Union:
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                return self._mock_value_for_annotation(non_none[0], name, prompt)
            return None

        if origin in (list, set, tuple) or annotation in (list, set, tuple):
            item_type = args[0] if args else None
            if isinstance(item_type, type) and issubclass(item_type, BaseModel):
                return [self._build_mock_instance(item_type, prompt)]
            return ["Demo item 1"]

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
                return "B" if "variation: b" in prompt.lower() else "A"
            if name == "content_text":
                return "JA Assure tailored insurance advisory copy.\n\n*Terms, conditions, and underwriting limits apply.*"
            return f"Demo generated {name} for query"
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

# Singleton provider instance
llm_provider = LLMProvider()
