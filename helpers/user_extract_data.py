"""
Preflight helper: extrai, normaliza e valida o texto do usuário
usando LangExtract (Vertex AI via ADC) antes de acionar o ADK.

Saída padrão: {
  "success": bool,
  "data": {
    "landing_page_url": str|None,
    "objetivo_final": str|None,
    "perfil_cliente": str|None,
    "formato_anuncio": str|None,
    "foco": str|None
  },
  "normalized": {
    "formato_anuncio_norm": str|None,
    "objetivo_final_norm": str|None
  },
  "errors": [{"field": str, "message": str}]
}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import os
import re
import logging

try:
    import langextract as lx
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "LangExtract is required. Install with: pip install langextract>=1.0.9"
    ) from exc


URL_REGEX = re.compile(r"^https?://[\w.-]+(\:[0-9]+)?(/.*)?$", re.IGNORECASE)


logger = logging.getLogger(__name__)


class UserInputExtractor:
    def __init__(self, model_id: str = "gemini-2.5-flash") -> None:
        self.model_id = model_id
        self.project = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        # Prompt para extração dos campos mínimos
        self.prompt = (
            "From the user text below, extract exactly these fields if present: "
            "landing_page_url (http/https), objetivo_final, perfil_cliente, formato_anuncio, foco, "
            "nome_empresa, o_que_a_empresa_faz, sexo_cliente_alvo. "
            "Use exact user wording for values when present. Do not invent. If a field is not present, leave empty. "
            "Normalize common synonyms only in attributes (not extraction_text). "
            "For sexo_cliente_alvo, map synonyms to masculino|feminino|neutro when possible."
        )

    def _examples(self) -> List[lx.data.ExampleData]:
        examples: List[lx.data.ExampleData] = []

        # Exemplo 1 – completo (linhas chave:valor)
        txt1 = (
            "landing_page_url: https://exemplo.com/landing\n"
            "objetivo_final: agendamentos de consulta via WhatsApp\n"
            "perfil_cliente: homens 35-50 anos, executivos com sobrepeso\n"
            "formato_anuncio: Reels\n"
            "foco: não engordar no inverno\n"
            "nome_empresa: Clínica Bem Viver\n"
            "o_que_a_empresa_faz: Clínica de nutrição e emagrecimento saudável\n"
            "sexo_cliente_alvo: homens maduros\n"
        )
        examples.append(
            lx.data.ExampleData(
                text=txt1,
                extractions=[
                    lx.data.Extraction(
                        extraction_class="landing_page_url",
                        extraction_text="https://exemplo.com/landing",
                    ),
                    lx.data.Extraction(
                        extraction_class="objetivo_final",
                        extraction_text="agendamentos de consulta via WhatsApp",
                        attributes={"normalized": "agendamentos"},
                    ),
                    lx.data.Extraction(
                        extraction_class="perfil_cliente",
                        extraction_text="homens 35-50 anos, executivos com sobrepeso",
                    ),
                    lx.data.Extraction(
                        extraction_class="formato_anuncio",
                        extraction_text="Reels",
                        attributes={"normalized": "Reels"},
                    ),
                    lx.data.Extraction(
                        extraction_class="foco",
                        extraction_text="não engordar no inverno",
                    ),
                    lx.data.Extraction(
                        extraction_class="nome_empresa",
                        extraction_text="Clínica Bem Viver",
                    ),
                    lx.data.Extraction(
                        extraction_class="o_que_a_empresa_faz",
                        extraction_text="Clínica de nutrição e emagrecimento saudável",
                    ),
                    lx.data.Extraction(
                        extraction_class="sexo_cliente_alvo",
                        extraction_text="homens maduros",
                        attributes={"normalized": "masculino"},
                    ),
                ],
            )
        )

        # Exemplo 2 – sinônimos (story → Stories; mensagens → agendamentos)
        txt2 = (
            "formato: story\n"
            "objetivo: mensagens no WhatsApp\n"
            "perfil: executivos 30-45 com pouco tempo\n"
            "nome da empresa: Agência Exemplo\n"
            "Descrição: Agência de marketing digital para profissionais autônomos\n"
            "público: todos os gêneros\n"
        )
        examples.append(
            lx.data.ExampleData(
                text=txt2,
                extractions=[
                    lx.data.Extraction(
                        extraction_class="formato_anuncio",
                        extraction_text="story",
                        attributes={"normalized": "Stories"},
                    ),
                    lx.data.Extraction(
                        extraction_class="objetivo_final",
                        extraction_text="mensagens no WhatsApp",
                        attributes={"normalized": "agendamentos"},
                    ),
                    lx.data.Extraction(
                        extraction_class="perfil_cliente",
                        extraction_text="executivos 30-45 com pouco tempo",
                    ),
                    lx.data.Extraction(
                        extraction_class="nome_empresa",
                        extraction_text="Agência Exemplo",
                    ),
                    lx.data.Extraction(
                        extraction_class="o_que_a_empresa_faz",
                        extraction_text="Agência de marketing digital para profissionais autônomos",
                    ),
                    lx.data.Extraction(
                        extraction_class="sexo_cliente_alvo",
                        extraction_text="todos os gêneros",
                        attributes={"normalized": "neutro"},
                    ),
                ],
            )
        )

        # Exemplo 3 – inválido (formato não suportado)
        txt3 = "formato_anuncio: anuncio rapido\n"
        examples.append(
            lx.data.ExampleData(
                text=txt3,
                extractions=[
                    lx.data.Extraction(
                        extraction_class="formato_anuncio",
                        extraction_text="anuncio rapido",
                        attributes={"normalized": ""},
                    )
                ],
            )
        )

        # Exemplo 4 – gênero feminino com sinônimos variados
        txt4 = (
            "landing page: https://exemplo.com/mulheres\n"
            "objetivo final: leads qualificados\n"
            "perfil: mulheres empreendedoras iniciantes\n"
            "formato: Feed\n"
            "empresa: Escola Start\n"
            "o que faz: Mentoria de negócios para mulheres\n"
            "gênero alvo: feminino\n"
        )
        examples.append(
            lx.data.ExampleData(
                text=txt4,
                extractions=[
                    lx.data.Extraction(
                        extraction_class="landing_page_url",
                        extraction_text="https://exemplo.com/mulheres",
                    ),
                    lx.data.Extraction(
                        extraction_class="objetivo_final",
                        extraction_text="leads qualificados",
                        attributes={"normalized": "leads"},
                    ),
                    lx.data.Extraction(
                        extraction_class="perfil_cliente",
                        extraction_text="mulheres empreendedoras iniciantes",
                    ),
                    lx.data.Extraction(
                        extraction_class="formato_anuncio",
                        extraction_text="Feed",
                        attributes={"normalized": "Feed"},
                    ),
                    lx.data.Extraction(
                        extraction_class="nome_empresa",
                        extraction_text="Escola Start",
                    ),
                    lx.data.Extraction(
                        extraction_class="o_que_a_empresa_faz",
                        extraction_text="Mentoria de negócios para mulheres",
                    ),
                    lx.data.Extraction(
                        extraction_class="sexo_cliente_alvo",
                        extraction_text="feminino",
                        attributes={"normalized": "feminino"},
                    ),
                ],
            )
        )
        return examples

    def extract(self, raw_text: str) -> Dict[str, Any]:
        logger = logging.getLogger(__name__)
        try:
            logger.info(
                "[preflight] user_extract_start: model=%s, project=%s, location=%s, text_len=%s, fewshots=%s",
                self.model_id,
                self.project,
                self.location,
                len(raw_text or ""),
                len(self._examples()),
            )
        except Exception:
            pass
        result = lx.extract(
            text_or_documents=raw_text,
            prompt_description=self.prompt,
            examples=self._examples(),
            model_id=self.model_id,
            extraction_passes=1,
            max_workers=4,
            max_char_buffer=1800,
            use_schema_constraints=True,
            fence_output=False,
            language_model_params={
                "vertexai": True,
                "project": self.project,
                "location": self.location,
            },
        )
        converted = self._convert(result)
        try:
            logger.info(
                "[preflight] user_extract_done: success=%s, formato_norm=%s, objetivo_norm=%s",
                converted.get("success"),
                converted.get("normalized", {}).get("formato_anuncio_norm"),
                converted.get("normalized", {}).get("objetivo_final_norm"),
            )
        except Exception:
            pass
        return converted

    def _convert(self, langextract_result: Any) -> Dict[str, Any]:
        data: Dict[str, Optional[str]] = {
            "landing_page_url": None,
            "objetivo_final": None,
            "perfil_cliente": None,
            "formato_anuncio": None,
            "foco": None,
            "nome_empresa": None,
            "o_que_a_empresa_faz": None,
            "sexo_cliente_alvo": None,
        }
        normalized: Dict[str, Optional[str]] = {
            "formato_anuncio_norm": None,
            "objetivo_final_norm": None,
            "sexo_cliente_alvo_norm": "neutro",
        }

        # Mapear extrações
        if hasattr(langextract_result, "extractions"):
            for ext in langextract_result.extractions:
                cls = getattr(ext, "extraction_class", "") or ""
                txt = getattr(ext, "extraction_text", "") or ""
                attrs = getattr(ext, "attributes", {}) or {}
                if cls in data and txt:
                    data[cls] = txt.strip()
                if cls == "formato_anuncio":
                    normalized["formato_anuncio_norm"] = self._normalize_formato(attrs.get("normalized") or txt)
                if cls == "objetivo_final":
                    normalized["objetivo_final_norm"] = self._normalize_objetivo(attrs.get("normalized") or txt)
                if cls == "sexo_cliente_alvo":
                    normalized["sexo_cliente_alvo_norm"] = self._normalize_sexo(attrs.get("normalized") or txt)

        try:
            logger.debug(
                "[preflight] convert_fields data_keys=%s normalized_keys=%s",
                list(data.keys()),
                list(normalized.keys()),
            )
        except Exception:
            pass

        errors: List[Dict[str, str]] = []

        # Validações mínimas
        if not data["landing_page_url"] or not URL_REGEX.match(data["landing_page_url"]):
            errors.append({"field": "landing_page_url", "message": "URL inválida ou ausente (http/https)."})

        fmt = normalized["formato_anuncio_norm"]
        if fmt not in {"Reels", "Stories", "Feed"}:
            errors.append({
                "field": "formato_anuncio",
                "message": "Valor não suportado. Use Reels|Stories|Feed."
            })

        obj = normalized["objetivo_final_norm"]
        if not obj:
            errors.append({
                "field": "objetivo_final",
                "message": "Objetivo final ausente/ambíguo. Ex.: agendamentos|leads|vendas|contato."
            })

        if not data["perfil_cliente"]:
            errors.append({"field": "perfil_cliente", "message": "Perfil/Persona ausente."})

        success = len(errors) == 0
        return {
            "success": success,
            "data": data,
            "normalized": normalized,
            "errors": errors,
        }

    @staticmethod
    def _normalize_formato(value: str | None) -> Optional[str]:
        if not value:
            return None
        v = value.strip().lower()
        if v in {"reel", "reels", "reels vídeo", "reels video"}:
            return "Reels"
        if v in {"story", "stories", "storie", "storys"}:
            return "Stories"
        if v in {"feed", "carrossel", "carousel"}:
            return "Feed"
        if v == "reels":
            return "Reels"
        return value.title()

    @staticmethod
    def _normalize_objetivo(value: str | None) -> Optional[str]:
        if not value:
            return None
        v = value.strip().lower()
        # Mapas simples de sinônimos
        if any(w in v for w in ["whats", "whatsapp", "mensagem", "mensagens", "conversa"]):
            return "agendamentos"
        if any(w in v for w in ["lead", "inscri", "cadastro"]):
            return "leads"
        if any(w in v for w in ["venda", "comprar", "compra"]):
            return "vendas"
        if any(w in v for w in ["contato", "fale", "ligar"]):
            return "contato"
        # fallback conservador
        return value

    @staticmethod
    def _normalize_sexo(value: str | None) -> str:
        if not value:
            return "neutro"

        v = value.strip().lower()
        if not v:
            return "neutro"

        masculino_aliases = {
            "masculino",
            "homem",
            "homens",
            "macho",
            "publico masculino",
        }
        feminino_aliases = {
            "feminino",
            "mulher",
            "mulheres",
            "publico feminino",
        }
        neutro_aliases = {
            "neutro",
            "todos",
            "ambos",
            "todos os gêneros",
            "todos os generos",
            "misto",
            "geral",
            "qualquer",
        }

        if v in masculino_aliases:
            return "masculino"
        if v in feminino_aliases:
            return "feminino"
        if v in neutro_aliases:
            return "neutro"

        if "masc" in v or "homem" in v:
            return "masculino"
        if "fem" in v or "mulher" in v:
            return "feminino"
        if any(token in v for token in ["neut", "todos", "ambos", "misto", "qualquer"]):
            return "neutro"

        return "neutro"


def extract_user_input(raw_text: str) -> Dict[str, Any]:
    extractor = UserInputExtractor()
    return extractor.extract(raw_text or "")
