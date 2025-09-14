"""
StoryBrand Schema for structured validation.
Defines Pydantic models for StoryBrand analysis output.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class ProblemTypes(BaseModel):
    """Os três níveis de problemas no framework StoryBrand."""
    external: str = Field(default="", description="Problema tangível/prático")
    internal: str = Field(default="", description="Sentimentos e frustrações")
    philosophical: str = Field(default="", description="Por que é errado/injusto")


class CharacterElement(BaseModel):
    """Elemento Character (Personagem) do StoryBrand."""
    description: str = Field(description="Descrição do cliente ideal")
    evidence: List[str] = Field(default_factory=list, description="Evidências extraídas")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confiança na extração")


class ProblemElement(BaseModel):
    """Elemento Problem (Problema) do StoryBrand."""
    description: str = Field(description="Principais problemas enfrentados")
    evidence: List[str] = Field(default_factory=list, description="Evidências extraídas")
    types: ProblemTypes = Field(default_factory=ProblemTypes, description="Tipos de problemas")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confiança na extração")


class GuideElement(BaseModel):
    """Elemento Guide (Guia) do StoryBrand."""
    description: str = Field(description="Como a marca se posiciona como guia")
    authority: str = Field(default="", description="Credenciais e experiência")
    empathy: str = Field(default="", description="Compreensão do problema do cliente")
    evidence: List[str] = Field(default_factory=list, description="Evidências extraídas")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confiança na extração")


class PlanElement(BaseModel):
    """Elemento Plan (Plano) do StoryBrand."""
    description: str = Field(description="Plano de ação proposto")
    steps: List[str] = Field(default_factory=list, description="Passos do plano")
    evidence: List[str] = Field(default_factory=list, description="Evidências extraídas")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confiança na extração")


class ActionElement(BaseModel):
    """Elemento Call to Action (Ação) do StoryBrand."""
    primary: str = Field(default="", description="CTA principal")
    secondary: str = Field(default="", description="CTA secundário")
    evidence: List[str] = Field(default_factory=list, description="Evidências extraídas")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confiança na extração")


class FailureElement(BaseModel):
    """Elemento Failure (Fracasso) do StoryBrand."""
    description: str = Field(description="Consequências de não agir")
    consequences: List[str] = Field(default_factory=list, description="Lista de consequências")
    evidence: List[str] = Field(default_factory=list, description="Evidências extraídas")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confiança na extração")


class SuccessElement(BaseModel):
    """Elemento Success (Sucesso) do StoryBrand."""
    description: str = Field(description="Transformação prometida")
    benefits: List[str] = Field(default_factory=list, description="Benefícios específicos")
    transformation: str = Field(default="", description="Transformação principal")
    evidence: List[str] = Field(default_factory=list, description="Evidências extraídas")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confiança na extração")


class StoryBrandMetadata(BaseModel):
    """Metadados da análise StoryBrand."""
    total_headings: int = Field(default=0, description="Total de headings analisados")
    total_ctas: int = Field(default=0, description="Total de CTAs encontrados")
    total_lists: int = Field(default=0, description="Total de listas analisadas")
    text_length: int = Field(default=0, description="Tamanho do texto analisado")


class StoryBrandAnalysis(BaseModel):
    """
    Análise completa do framework StoryBrand.

    Este modelo estrutura os 7 elementos do StoryBrand de Donald Miller,
    fornecendo uma análise narrativa completa da página analisada.
    """

    character: CharacterElement = Field(
        description="O cliente como herói da história"
    )
    problem: ProblemElement = Field(
        description="Os problemas que o cliente enfrenta"
    )
    guide: GuideElement = Field(
        description="A marca como guia/mentor"
    )
    plan: PlanElement = Field(
        description="O plano de ação proposto"
    )
    action: ActionElement = Field(
        description="Calls to action"
    )
    failure: FailureElement = Field(
        description="O que acontece se não agir"
    )
    success: SuccessElement = Field(
        description="A transformação desejada"
    )
    completeness_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score de completude da análise (0-1)"
    )
    metadata: StoryBrandMetadata = Field(
        default_factory=StoryBrandMetadata,
        description="Metadados da análise"
    )

    def to_summary(self) -> str:
        """Gera um resumo textual da análise StoryBrand."""
        summary = []

        if self.character.description:
            summary.append(f"**Cliente Ideal**: {self.character.description}")

        if self.problem.description:
            summary.append(f"**Problema Principal**: {self.problem.description}")

        if self.guide.authority or self.guide.empathy:
            guide_text = f"**Nossa Posição**: "
            if self.guide.authority:
                guide_text += f"{self.guide.authority}"
            if self.guide.empathy:
                guide_text += f" - {self.guide.empathy}"
            summary.append(guide_text)

        if self.plan.steps:
            summary.append(f"**Plano**: {len(self.plan.steps)} passos para o sucesso")

        if self.action.primary:
            summary.append(f"**Ação Principal**: {self.action.primary}")

        if self.failure.consequences:
            summary.append(f"**Riscos**: {', '.join(self.failure.consequences[:2])}")

        if self.success.transformation:
            summary.append(f"**Transformação**: {self.success.transformation}")

        return "\n".join(summary)

    def to_ad_context(self) -> Dict[str, any]:
        """
        Converte a análise StoryBrand em contexto para geração de anúncios.

        Returns:
            Dict com elementos relevantes para criação de anúncios
        """
        return {
            "persona": self.character.description,
            "dores_principais": [
                self.problem.types.external,
                self.problem.types.internal
            ],
            "proposta_valor": self.guide.description,
            "autoridade": self.guide.authority,
            "plano_simplificado": self.plan.steps[:3] if self.plan.steps else [],
            "cta_principal": self.action.primary,
            "cta_secundario": self.action.secondary,
            "urgencia": self.failure.consequences[:2] if self.failure.consequences else [],
            "beneficios": self.success.benefits[:5] if self.success.benefits else [],
            "transformacao": self.success.transformation,
            "confianca_analise": self.completeness_score
        }

    class Config:
        json_encoders = {
            float: lambda v: round(v, 2)
        }