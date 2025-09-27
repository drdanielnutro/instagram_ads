"""Configuration objects describing StoryBrand fallback sections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class StoryBrandSectionConfig:
    """Represents a section executed during the fallback pipeline."""

    state_key: str
    prompt_name: str
    narrative_goal: str


def build_storybrand_section_configs() -> List[StoryBrandSectionConfig]:
    return [
        StoryBrandSectionConfig(
            state_key="storybrand_character",
            prompt_name="section_character",
            narrative_goal="Definir com clareza quem é o herói da história.",
        ),
        StoryBrandSectionConfig(
            state_key="exposition_1",
            prompt_name="section_exposition_1",
            narrative_goal="Apresentar a situação inicial do cliente antes do conflito.",
        ),
        StoryBrandSectionConfig(
            state_key="inciting_incident_1",
            prompt_name="section_inciting_incident_1",
            narrative_goal="Destacar o primeiro gatilho que evidencia o problema.",
        ),
        StoryBrandSectionConfig(
            state_key="exposition_2",
            prompt_name="section_exposition_2",
            narrative_goal="Aprofundar o contexto com detalhes visuais e emocionais.",
        ),
        StoryBrandSectionConfig(
            state_key="inciting_incident_2",
            prompt_name="section_inciting_incident_2",
            narrative_goal="Reforçar o problema com um segundo gatilho complementar.",
        ),
        StoryBrandSectionConfig(
            state_key="unmet_needs_summary",
            prompt_name="section_unmet_needs",
            narrative_goal="Sintetizar necessidades não atendidas que justificam a proposta.",
        ),
        StoryBrandSectionConfig(
            state_key="storybrand_problem_external",
            prompt_name="section_problem_external",
            narrative_goal="Nomear o problema externo enfrentado pelo cliente.",
        ),
        StoryBrandSectionConfig(
            state_key="storybrand_problem_internal",
            prompt_name="section_problem_internal",
            narrative_goal="Explorar as dores internas e emocionais.",
        ),
        StoryBrandSectionConfig(
            state_key="storybrand_problem_philosophical",
            prompt_name="section_problem_philosophical",
            narrative_goal="Explicar por que é injusto o cliente enfrentar esse problema.",
        ),
        StoryBrandSectionConfig(
            state_key="storybrand_guide",
            prompt_name="section_guide",
            narrative_goal="Posicionar a empresa como guia confiável.",
        ),
        StoryBrandSectionConfig(
            state_key="storybrand_value_proposition",
            prompt_name="section_value_proposition",
            narrative_goal="Explicar como a empresa entrega a transformação prometida.",
        ),
        StoryBrandSectionConfig(
            state_key="storybrand_plan",
            prompt_name="section_plan",
            narrative_goal="Apresentar um plano em passos claros e acionáveis.",
        ),
        StoryBrandSectionConfig(
            state_key="storybrand_action",
            prompt_name="section_action",
            narrative_goal="Convocar o cliente para a ação com CTA direto e secundário.",
        ),
        StoryBrandSectionConfig(
            state_key="storybrand_failure",
            prompt_name="section_failure",
            narrative_goal="Mostrar riscos de não agir.",
        ),
        StoryBrandSectionConfig(
            state_key="storybrand_success",
            prompt_name="section_success",
            narrative_goal="Descrever os resultados positivos alcançados.",
        ),
        StoryBrandSectionConfig(
            state_key="storybrand_identity",
            prompt_name="section_identity",
            narrative_goal="Conectar a nova identidade do cliente após o sucesso.",
        ),
    ]


__all__ = ["StoryBrandSectionConfig", "build_storybrand_section_configs"]
