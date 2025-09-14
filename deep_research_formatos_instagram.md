# Deep Research: Definição de Campos Específicos por Formato de Anúncio Instagram

## Contexto do Problema

Atualmente nosso sistema de geração de anúncios Instagram trata todos os formatos (Reels, Stories, Feed) de forma praticamente idêntica, alterando apenas o aspect_ratio das imagens. Isso ignora diferenças fundamentais entre os formatos em termos de:
- Tipo de mídia (imagem estática, vídeo, carrossel)
- Estilo de copy e estrutura narrativa
- Posicionamento no funil de vendas
- Comportamento do usuário esperado
- CTAs disponíveis e mais efetivos

## Objetivo da Pesquisa

Definir com precisão **quais campos cada formato de anúncio deve ter** e **como o conteúdo deve variar** entre Reels, Stories e Feed para maximizar a efetividade de cada formato.

## Perguntas Fundamentais para a Pesquisa

### 1. ESTRUTURA DE DADOS POR FORMATO

Para cada formato (Reels, Stories, Feed), defina:

#### A) Campos de Mídia
- **tipo_midia**: "video" | "imagem" | "carrossel" | "foto_sequencial" (para photo reels)
- **duracao_video**: aplicável? Se sim, qual range ideal para cada formato?
- **num_cards_carrossel**: aplicável? Se sim, quantos cards (2-10)?
- **tem_audio**: aplicável? É obrigatório? (considerar anúncios vs orgânico)
- **tipo_audio**: "musica_trending" | "voz_off" | "sem_audio" | "efeitos_sonoros" | "audio_original"
- **e_anuncio_pago**: boolean (afeta especificações e CTAs disponíveis)

#### B) Campos de Copy Específicos
- **tem_texto_sobreposto**: O texto aparece sobre a imagem/vídeo?
- **posicao_texto_sobreposto**: "centro" | "topo" | "rodape" | "lateral"
- **limite_caracteres_headline**: Qual o ideal para cada formato?
- **limite_caracteres_corpo**: Qual o ideal para cada formato?
- **estrutura_narrativa**: "gancho-desenvolvimento-cta" | "problema-solucao" | "storytelling" | "lista" | "tutorial"
- **copy_legenda_separada**: boolean (texto na descrição do post)

#### C) Campos de Engajamento
- **cta_nativo_organico**: Quais CTAs disponíveis sem pagar? (ex: "link na bio")
- **cta_anuncio_pago**: Quais botões de CTA disponíveis para ads? (ex: "Saiba mais", "Comprar agora")
- **interatividade**: Possui polls, quiz, countdown, stickers? (Stories específico)
- **link_sticker_disponivel**: Aplicável em Stories? Requisitos?
- **shopping_tags**: Produtos podem ser taggeados? Quantos?
- **branded_content_tag**: É conteúdo de parceria/colaboração?

### 2. ESTRATÉGIA POR FORMATO

Para cada formato, especifique:

#### A) Posicionamento no Funil
```
TOPO (Awareness):
- Qual formato funciona melhor?
- Que tipo de conteúdo?
- Métricas principais?

MEIO (Consideração):
- Qual formato funciona melhor?
- Que tipo de conteúdo?
- Métricas principais?

FUNDO (Conversão):
- Qual formato funciona melhor?
- Que tipo de conteúdo?
- Métricas principais?
```

#### B) Casos de Uso Ideais
- **Reels**: Quando escolher? Para qual objetivo?
- **Stories**: Quando escolher? Para qual objetivo?
- **Feed**: Quando escolher? Para qual objetivo?

### 3. ESPECIFICAÇÕES TÉCNICAS ATUALIZADAS (2024/2025)

#### A) Reels
- Duração mínima e máxima permitida
- Aspect ratios aceitos
- Formatos de arquivo suportados
- Tamanho máximo do arquivo
- Especificações de áudio
- Limitações de texto sobreposto
- Diferenças entre Reels orgânicos e Reels Ads

#### B) Stories
- Duração por slide (imagem vs vídeo)
- Aspect ratios aceitos
- Elementos interativos disponíveis
- Link stickers (requisitos)
- Formatos de arquivo suportados

#### C) Feed
- Tipos aceitos (single, carousel, video)
- Aspect ratios por tipo
- Limite de cards no carrossel
- Duração máxima de vídeo
- Especificações para cada tipo

### 4. SCHEMA JSON PROPOSTO

Baseado na pesquisa, proponha um schema JSON otimizado que contemple:

```json
{
  "formato": "Reels|Stories|Feed",
  "contexto_uso": "organico|anuncio_pago",
  "tipo_conteudo": {
    "midia": {
      "tipo": "video|imagem|carrossel|foto_sequencial",
      "duracao_segundos": null | number,
      "num_elementos": number,
      "aspect_ratio": "9:16|1:1|4:5|16:9",
      "tem_audio": boolean,
      "tipo_audio": "...",
      "especificacoes_tecnicas": {
        "tamanho_max_mb": number,
        "resolucao_min": "...",
        "formatos_aceitos": [...]
      }
    },
    "copy": {
      "estrutura_narrativa": "...",
      "texto_sobreposto": {
        "tem": boolean,
        "posicao": "...",
        "limite_caracteres": number
      },
      "legenda": {
        "limite_caracteres": number,
        "estrutura": "..."
      },
      "hashtags": {
        "quantidade_recomendada": number,
        "posicionamento": "inline|primeiro_comentario"
      }
    },
    "interatividade": {
      "elementos_interativos": [...],
      "cta_organico": "...",
      "cta_pago": "...",
      "shopping_habilitado": boolean,
      "link_direto": boolean
    }
  },
  "estrategia": {
    "etapa_funil": "topo|meio|fundo",
    "objetivo_campanha": "...",
    "metricas_principais": [...],
    "publico_alvo": {
      "temperatura": "frio|morno|quente",
      "comportamento_esperado": "..."
    }
  },
  "validacoes": {
    "politicas_aplicaveis": [...],
    "restricoes_setor": [...]
  }
}
```

### 5. REGRAS DE NEGÓCIO

Defina regras claras como:

1. **Se formato = "Reels"**, então:
   - tipo_midia PODE ser "video" ou "foto_sequencial" (photo reels)
   - Se video: duracao ENTRE 3-90 segundos (orgânico) ou 3-60 segundos (ads)
   - Se foto_sequencial: 2-10 fotos com transições automáticas
   - copy.headline MÁXIMO 40 caracteres (sobreposto)
   - audio RECOMENDADO (trending para orgânico, licenciado para ads)

2. **Se formato = "Stories"**, então:
   - tipo_midia PODE ser "video" ou "imagem"
   - interatividade.elementos DEVE incluir pelo menos 1
   - copy.estrutura DEVE ser "urgencia" ou "escassez"

3. **Se formato = "Feed"**, então:
   - tipo_midia PODE ser "imagem", "carrossel" ou "video"
   - Se "carrossel", num_cards ENTRE 2-10
   - copy.corpo PODE ser mais longo (até 2200 caracteres)

### 6. EXEMPLOS PRÁTICOS

Para cada formato, forneça 3 exemplos reais de anúncios de alta performance em 2024/2025, analisando:

#### Exemplo Reels:
```
Marca: [Nome]
Objetivo: [Qual era]
Duração: [Segundos]
Estrutura: [Como foi construído]
Copy: [Transcrição]
CTA: [Qual usado]
Resultado: [Métrica de sucesso]
Por que funcionou: [Análise]
```

#### Exemplo Stories:
```
[Mesma estrutura]
```

#### Exemplo Feed:
```
[Mesma estrutura]
```

### 7. VALIDAÇÕES E CONFORMIDADE

Liste as políticas do Instagram que impactam cada formato:

#### Reels:
- Restrições de conteúdo
- Requisitos de originalidade
- Políticas de música/áudio

#### Stories:
- Limitações de links
- Regras para conteúdo promocional
- Restrições de interatividade

#### Feed:
- Proporção texto/imagem
- Políticas de antes/depois
- Restrições de alegações

### 8. OTIMIZAÇÕES POR SETOR

Como adaptar cada formato para diferentes nichos:

#### Saúde/Bem-estar:
- Reels: [Estratégia específica]
- Stories: [Estratégia específica]
- Feed: [Estratégia específica]

#### E-commerce/Varejo:
- Reels: [Estratégia específica]
- Stories: [Estratégia específica]
- Feed: [Estratégia específica]

#### Serviços/B2B:
- Reels: [Estratégia específica]
- Stories: [Estratégia específica]
- Feed: [Estratégia específica]

## Output Esperado

Ao final da pesquisa, esperamos ter:

1. **Definição clara** de quais campos são obrigatórios, opcionais e proibidos para cada formato
2. **Schema JSON definitivo** que o sistema deve implementar
3. **Regras de validação** para garantir conformidade
4. **Guia de melhores práticas** para geração de conteúdo
5. **Matriz de decisão** para escolha automática de formato baseada em objetivo

## Instruções para a IA Pesquisadora

1. Use dados e estudos recentes (2024/2025)
2. Priorize informações do mercado brasileiro
3. Considere mudanças recentes nas políticas do Instagram/Meta:
   - Fim do IGTV (migrado para Reels)
   - Link stickers substituindo swipe up
   - Photo Reels como nova opção
   - Mudanças em durações máximas permitidas
4. **Diferencie claramente** entre:
   - Conteúdo orgânico vs Anúncios pagos
   - CTAs disponíveis para cada contexto
   - Limitações técnicas de cada tipo
5. Inclua insights de Social Media Managers e Performance Marketers brasileiros
6. Baseie-se em casos reais de sucesso mensuráveis no Brasil
7. Para cada recomendação, especifique:
   - Se aplica a orgânico, pago ou ambos
   - Requisitos mínimos (seguidores, conta business, etc)
   - Custo-benefício da escolha
8. Forneça referências e fontes oficiais do Meta Business

## Resultado Final Desejado

Um documento estruturado que permita:
- Refatorar o sistema atual para gerar conteúdo verdadeiramente otimizado por formato
- Validar automaticamente se o conteúdo gerado está adequado ao formato escolhido
- Maximizar a performance de cada anúncio respeitando as características únicas de cada formato
- Criar uma base de conhecimento que evolua com as mudanças da plataforma

---

**IMPORTANTE**: Esta pesquisa deve resultar em especificações técnicas implementáveis, não apenas diretrizes teóricas. Cada recomendação deve ser traduzível em código e validações específicas.