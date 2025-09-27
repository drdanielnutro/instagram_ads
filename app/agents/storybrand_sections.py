"""Configuration objects describing StoryBrand fallback sections."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping


@dataclass(frozen=True)
class StoryBrandSectionConfig:
    """Represents a section executed during the fallback pipeline."""

    state_key: str
    display_name: str
    writer_prompt_path: Path
    review_prompt_paths: Mapping[str, Path]
    corrector_prompt_path: Path
    narrative_goal: str


PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts" / "storybrand_fallback"
REVIEW_PROMPT_PATHS = {
    "masculino": PROMPT_DIR / "review_masculino.txt",
    "feminino": PROMPT_DIR / "review_feminino.txt",
}
CORRECTOR_PROMPT_PATH = PROMPT_DIR / "corrector.txt"


def _build_config(
    *,
    state_key: str,
    prompt_filename: str,
    display_name: str,
    narrative_goal: str,
) -> StoryBrandSectionConfig:
    return StoryBrandSectionConfig(
        state_key=state_key,
        display_name=display_name,
        writer_prompt_path=PROMPT_DIR / prompt_filename,
        review_prompt_paths=dict(REVIEW_PROMPT_PATHS),
        corrector_prompt_path=CORRECTOR_PROMPT_PATH,
        narrative_goal=narrative_goal,
    )


def build_storybrand_section_configs() -> List[StoryBrandSectionConfig]:
    return [
        _build_config(
            state_key="storybrand_character",
            prompt_filename="section_character.txt",
            display_name="StoryBrand – Personagem",
            narrative_goal="Definir com clareza quem é o herói da história.",
        ),
        _build_config(
            state_key="exposition_1",
            prompt_filename="section_exposition_1.txt",
            display_name="Exposição Inicial",
            narrative_goal="Apresentar a situação inicial do cliente antes do conflito.",
        ),
        _build_config(
            state_key="inciting_incident_1",
            prompt_filename="section_inciting_incident_1.txt",
            display_name="Incidente Inicial 1",
            narrative_goal="Destacar o primeiro gatilho que evidencia o problema.",
        ),
        _build_config(
            state_key="exposition_2",
            prompt_filename="section_exposition_2.txt",
            display_name="Exposição Complementar",
            narrative_goal="Aprofundar o contexto com detalhes visuais e emocionais.",
        ),
        _build_config(
            state_key="inciting_incident_2",
            prompt_filename="section_inciting_incident_2.txt",
            display_name="Incidente Inicial 2",
            narrative_goal="Reforçar o problema com um segundo gatilho complementar.",
        ),
        _build_config(
            state_key="unmet_needs_summary",
            prompt_filename="section_unmet_needs.txt",
            display_name="Necessidades Não Atendidas",
            narrative_goal="Sintetizar necessidades não atendidas que justificam a proposta.",
        ),
        _build_config(
            state_key="storybrand_problem_external",
            prompt_filename="section_problem_external.txt",
            display_name="Problema Externo",
            narrative_goal="Nomear o problema externo enfrentado pelo cliente.",
        ),
        _build_config(
            state_key="storybrand_problem_internal",
            prompt_filename="section_problem_internal.txt",
            display_name="Problema Interno",
            narrative_goal="Explorar as dores internas e emocionais.",
        ),
        _build_config(
            state_key="storybrand_problem_philosophical",
            prompt_filename="section_problem_philosophical.txt",
            display_name="Problema Filosófico",
            narrative_goal="Explicar por que é injusto o cliente enfrentar esse problema.",
        ),
        _build_config(
            state_key="storybrand_guide",
            prompt_filename="section_guide.txt",
            display_name="Guia",
            narrative_goal="Posicionar a empresa como guia confiável.",
        ),
        _build_config(
            state_key="storybrand_value_proposition",
            prompt_filename="section_value_proposition.txt",
            display_name="Proposta de Valor",
            narrative_goal="Explicar como a empresa entrega a transformação prometida.",
        ),
        _build_config(
            state_key="storybrand_plan",
            prompt_filename="section_plan.txt",
            display_name="Plano",
            narrative_goal="Apresentar um plano em passos claros e acionáveis.",
        ),
        _build_config(
            state_key="storybrand_action",
            prompt_filename="section_action.txt",
            display_name="Chamado à Ação",
            narrative_goal="Convocar o cliente para a ação com CTA direto e secundário.",
        ),
        _build_config(
            state_key="storybrand_failure",
            prompt_filename="section_failure.txt",
            display_name="Consequências da Inação",
            narrative_goal="Mostrar riscos de não agir.",
        ),
        _build_config(
            state_key="storybrand_success",
            prompt_filename="section_success.txt",
            display_name="Sucesso",
            narrative_goal="Descrever os resultados positivos alcançados.",
        ),
        _build_config(
            state_key="storybrand_identity",
            prompt_filename="section_identity.txt",
            display_name="Nova Identidade",
            narrative_goal="Conectar a nova identidade do cliente após o sucesso.",
        ),
    ]


__all__ = ["StoryBrandSectionConfig", "build_storybrand_section_configs"]
