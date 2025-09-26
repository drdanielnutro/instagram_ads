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

        self.enable_new_input_fields = (
            os.getenv("ENABLE_NEW_INPUT_FIELDS", "false").lower() == "true"
        )
        self.preflight_shadow_mode = (
            os.getenv("PREFLIGHT_SHADOW_MODE", "true").lower() == "true"
        )

        include_new_fields = self.enable_new_input_fields or self.preflight_shadow_mode

        base_prompt = (
            "From the user text below, extract exactly these fields if present: "
            "landing_page_url (http/https), objetivo_final, perfil_cliente, formato_anuncio, foco"
        )
        if include_new_fields:
            base_prompt += (
                ", nome_empresa (obrigatório), "
                "o_que_a_empresa_faz (CRÍTICO: capture a frase completa que descreve como "
                "a empresa transforma a vida dos clientes - ex.: 'Ajudamos X a conseguir Y "
                "através de Z'), "
                "sexo_cliente_alvo (obrigatório; somente masculino ou feminino)"
            )
        base_prompt += (
            ". Para campos simples (nome, URL, formato, objetivo, foco), preserve o texto "
            "original do usuário. "
            "Para o_que_a_empresa_faz: quando o texto estiver genérico ou incompleto, "
            "ENRIQUEÇA criando uma frase completa de transformação usando todos os "
            "campos disponíveis (perfil_cliente, sexo_cliente_alvo, objetivo_final, foco). "
            "Formato ideal: 'Ajudamos [QUEM] a [CONSEGUIR O QUÊ] através de [COMO]'. "
            "Se um campo não estiver presente, deixe vazio. Normalize sinônimos apenas "
            "em attributes, mantendo extraction_text coerente com a instrução."
        )
        if include_new_fields:
            base_prompt += (
                " Para sexo_cliente_alvo, mapeie qualquer sinônimo para masculino ou feminino. "
                "Nunca retorne neutro ou valores vazios para campos obrigatórios. "
                "Para o_que_a_empresa_faz, rejeite descrições genéricas como 'Consultoria'."
            )

        # Prompt para extração dos campos mínimos
        self.prompt = base_prompt

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
            "o_que_a_empresa_faz: Ajudamos executivos com sobrepeso a recuperar saúde e energia "
            "com programas personalizados de nutrição\n"
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
                        extraction_text=(
                            "Ajudamos executivos com sobrepeso a recuperar saúde e energia "
                            "com programas personalizados de nutrição"
                        ),
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
            "Descrição: Ajudamos profissionais autônomos a conquistar clientes consistentes "
            "com campanhas digitais personalizadas\n"
            "público: homens autônomos e consultores\n"
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
                        extraction_text=(
                            "Ajudamos profissionais autônomos a conquistar clientes consistentes "
                            "com campanhas digitais personalizadas"
                        ),
                    ),
                    lx.data.Extraction(
                        extraction_class="sexo_cliente_alvo",
                        extraction_text="homens autônomos",
                        attributes={"normalized": "masculino"},
                    ),
                ],
            )
        )

        # Exemplo 2b – descrição vaga permanece para ser barrada na validação
        txt2b = (
            "Descrição: Consultoria empresarial\n"
            "público: empresários e gestores\n"
        )
        examples.append(
            lx.data.ExampleData(
                text=txt2b,
                extractions=[
                    lx.data.Extraction(
                        extraction_class="o_que_a_empresa_faz",
                        extraction_text="Consultoria empresarial",
                    )
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

        # Exemplo 5 – enriquecimento masculino a partir de descrição genérica
        txt5 = (
            "empresa: Clínica Vitalidade\n"
            "descrição: tratamento médico para emagrecer\n"
            "perfil: homens executivos 40-50 anos\n"
            "sexo: masculino\n"
            "objetivo: agendamentos\n"
        )
        examples.append(
            lx.data.ExampleData(
                text=txt5,
                extractions=[
                    lx.data.Extraction(
                        extraction_class="nome_empresa",
                        extraction_text="Clínica Vitalidade",
                    ),
                    lx.data.Extraction(
                        extraction_class="o_que_a_empresa_faz",
                        extraction_text="tratamento médico para emagrecer",
                        attributes={
                            "enriched": (
                                "Ajudamos executivos acima dos 40 a recuperar energia e forma física "
                                "através de tratamento médico personalizado para emagrecimento sustentável"
                            )
                        },
                    ),
                    lx.data.Extraction(
                        extraction_class="perfil_cliente",
                        extraction_text="homens executivos 40-50 anos",
                    ),
                    lx.data.Extraction(
                        extraction_class="sexo_cliente_alvo",
                        extraction_text="masculino",
                        attributes={"normalized": "masculino"},
                    ),
                    lx.data.Extraction(
                        extraction_class="objetivo_final",
                        extraction_text="agendamentos",
                        attributes={"normalized": "agendamentos"},
                    ),
                ],
            )
        )

        # Exemplo 6 – enriquecimento feminino com contexto familiar
        txt6 = (
            "nome: Espaço Bem-Estar\n"
            "serviço: consultoria nutricional\n"
            "público: mulheres mães 30-40\n"
            "sexo alvo: feminino\n"
            "meta: leads\n"
        )
        examples.append(
            lx.data.ExampleData(
                text=txt6,
                extractions=[
                    lx.data.Extraction(
                        extraction_class="nome_empresa",
                        extraction_text="Espaço Bem-Estar",
                    ),
                    lx.data.Extraction(
                        extraction_class="o_que_a_empresa_faz",
                        extraction_text="consultoria nutricional",
                        attributes={
                            "enriched": (
                                "Ajudamos mães ocupadas a cuidar da alimentação de toda a família "
                                "através de consultoria nutricional prática e personalizada"
                            )
                        },
                    ),
                    lx.data.Extraction(
                        extraction_class="perfil_cliente",
                        extraction_text="mulheres mães 30-40",
                    ),
                    lx.data.Extraction(
                        extraction_class="sexo_cliente_alvo",
                        extraction_text="feminino",
                        attributes={"normalized": "feminino"},
                    ),
                    lx.data.Extraction(
                        extraction_class="objetivo_final",
                        extraction_text="leads",
                        attributes={"normalized": "leads"},
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
        include_new_fields = self.enable_new_input_fields or self.preflight_shadow_mode

        data: Dict[str, Optional[str]] = {
            "landing_page_url": None,
            "objetivo_final": None,
            "perfil_cliente": None,
            "formato_anuncio": None,
            "foco": None,
        }
        if include_new_fields:
            data.update(
                {
                    "nome_empresa": None,
                    "o_que_a_empresa_faz": None,
                    "sexo_cliente_alvo": None,
                }
            )

        normalized: Dict[str, Optional[str]] = {
            "formato_anuncio_norm": None,
            "objetivo_final_norm": None,
        }
        if include_new_fields:
            normalized.update({"sexo_cliente_alvo_norm": None})

        # Mapear extrações
        if hasattr(langextract_result, "extractions"):
            for ext in langextract_result.extractions:
                cls = getattr(ext, "extraction_class", "") or ""
                txt = getattr(ext, "extraction_text", "") or ""
                attrs = getattr(ext, "attributes", {}) or {}
                if cls in data and txt:
                    data[cls] = txt.strip()
                if cls == "o_que_a_empresa_faz":
                    enriched = (attrs.get("enriched") or "").strip()
                    if enriched:
                        data[cls] = enriched
                if cls == "formato_anuncio":
                    normalized["formato_anuncio_norm"] = self._normalize_formato(
                        attrs.get("normalized") or txt
                    )
                if cls == "objetivo_final":
                    normalized["objetivo_final_norm"] = self._normalize_objetivo(
                        attrs.get("normalized") or txt
                    )
                if include_new_fields and cls == "sexo_cliente_alvo":
                    normalized["sexo_cliente_alvo_norm"] = self._normalize_sexo(
                        attrs.get("normalized") or txt
                    )

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
            errors.append(
                {
                    "field": "formato_anuncio",
                    "message": "Valor não suportado. Use Reels|Stories|Feed.",
                }
            )

        obj = normalized["objetivo_final_norm"]
        if not obj:
            errors.append(
                {
                    "field": "objetivo_final",
                    "message": "Objetivo final ausente/ambíguo. Ex.: agendamentos|leads|vendas|contato.",
                }
            )

        if not data["perfil_cliente"]:
            errors.append({"field": "perfil_cliente", "message": "Perfil/Persona ausente."})

        if self.enable_new_input_fields:
            nome_empresa = (data.get("nome_empresa") or "").strip()
            descricao = (data.get("o_que_a_empresa_faz") or "").strip()
            sexo_norm = (normalized.get("sexo_cliente_alvo_norm") or "").strip()

            if not nome_empresa or len(nome_empresa) < 2:
                errors.append(
                    {
                        "field": "nome_empresa",
                        "message": "Nome da empresa é obrigatório (mínimo 2 caracteres).",
                    }
                )
            elif len(nome_empresa) > 100:
                errors.append(
                    {
                        "field": "nome_empresa",
                        "message": "Nome da empresa deve ter no máximo 100 caracteres.",
                    }
                )
            else:
                data["nome_empresa"] = nome_empresa

            if not descricao:
                errors.append(
                    {
                        "field": "o_que_a_empresa_faz",
                        "message": "Descrição da empresa é obrigatória (mínimo 30 caracteres).",
                    }
                )
            elif len(descricao) > 200:
                errors.append(
                    {
                        "field": "o_que_a_empresa_faz",
                        "message": "Descrição da empresa deve ter no máximo 200 caracteres.",
                    }
                )
            elif not self._is_transformational_description(descricao):
                errors.append(
                    {
                        "field": "o_que_a_empresa_faz",
                        "message": (
                            "Descreva a TRANSFORMAÇÃO que você oferece aos clientes. "
                            "Exemplo bom: 'Ajudamos mães a organizar rotina familiar em 30 dias'. "
                            "Exemplo ruim: 'Consultoria familiar'. "
                            "Inclua: QUEM você ajuda + COMO + QUAL RESULTADO."
                        ),
                    }
                )
            else:
                descricao_compact = " ".join(descricao.split())
                # TODO: extrair palavras-chave da transformação para enriquecer o fallback
                # quando os prompts suportarem contexto adicional.
                data["o_que_a_empresa_faz"] = descricao_compact

            if sexo_norm not in {"masculino", "feminino"}:
                errors.append(
                    {
                        "field": "sexo_cliente_alvo",
                        "message": "sexo_cliente_alvo é obrigatório (masculino ou feminino).",
                    }
                )
            else:
                normalized["sexo_cliente_alvo_norm"] = sexo_norm

        success = len(errors) == 0
        return {
            "success": success,
            "data": data,
            "normalized": normalized,
            "errors": errors,
        }

    @staticmethod
    def _is_transformational_description(descricao: str) -> bool:
        """Valida se a descrição comunica transformação acionável."""

        if not descricao:
            return False

        clean = descricao.strip()
        if len(clean) < 30:
            return False

        desc_lower = clean.lower()

        if desc_lower.startswith("ajudamos") and " a " in desc_lower:
            return True

        action_verbs = [
            "ajud",
            "transform",
            "capacit",
            "auxili",
            "gui",
            "facilit",
            "oferec",
            "fornec",
            "entreg",
            "possibilit",
            "cria",
            "criar",
            "desenvolv",
        ]
        has_action = any(verb in desc_lower for verb in action_verbs)

        result_connectors = [" para ", " através ", " com ", " até ", " em "]
        has_result = any(conn in desc_lower for conn in result_connectors)

        if has_action and (has_result or len(clean) > 50):
            return True

        generic_single_terms = {
            "consulta",
            "consultoria",
            "consultoria empresarial",
            "servicos",
            "serviços",
            "servico",
            "serviço",
            "empresa",
            "negocio",
            "negócio",
        }
        if desc_lower in generic_single_terms and len(clean.split()) <= 2:
            return False

        return has_action

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
    def _normalize_sexo(value: str | None) -> Optional[str]:
        if not value:
            return None

        v = value.strip().lower()
        if not v:
            return None

        masculino_aliases = {
            "masculino",
            "homem",
            "homens",
            "macho",
            "publico masculino",
            "male",
            "men",
        }
        feminino_aliases = {
            "feminino",
            "mulher",
            "mulheres",
            "publico feminino",
            "female",
            "women",
        }

        if v in masculino_aliases or "masc" in v or "homem" in v:
            return "masculino"
        if v in feminino_aliases or "fem" in v or "mulher" in v:
            return "feminino"

        return None


def extract_user_input(raw_text: str) -> Dict[str, Any]:
    extractor = UserInputExtractor()
    return extractor.extract(raw_text or "")
