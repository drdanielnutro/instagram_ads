export type AspectRatio = "4:5" | "9:16" | "1:1";

export interface VisualInfo {
  descricao_imagem?: string;
  prompt_estado_atual?: string;
  prompt_estado_intermediario?: string;
  prompt_estado_aspiracional?: string;
  aspect_ratio?: AspectRatio | string;
  images?: string[];
}

export interface CopyInfo {
  headline?: string;
  corpo?: string;
  cta_texto?: string;
}

export interface AdVariation {
  landing_page_url?: string;
  formato?: "Feed" | "Reels" | "Stories" | string;
  copy?: CopyInfo;
  visual?: VisualInfo;
  cta_instagram?: string;
  fluxo?: string;
  referencia_padroes?: string;
  contexto_landing?: unknown;
}
