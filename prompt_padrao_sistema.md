# Formato de Entrada para Geração de Anúncios Instagram

## Campos Principais

### Campos OBRIGATÓRIOS
- **landing_page_url**: URL da página de destino do anúncio
- **objetivo_final**: O que você quer alcançar com o anúncio
- **perfil_cliente**: Descrição detalhada da persona/público-alvo
- **formato_anuncio**: Formato do anúncio (Reels, Stories ou Feed)

### Campo OPCIONAL (mas recomendado)
- **foco**: Tema ou gancho específico da campanha (ex: liquidação, sazonalidade, benefício específico)

## Formatos de Entrada Aceitos

### Formato 1: Chave-valor (RECOMENDADO)
```
landing_page_url: https://nutrologodivinopolis.com.br/masculino/
objetivo_final: agendamentos
perfil_cliente: descrição da persona e suas dores
formato_anuncio: Reels
foco: liquidação de inverno
```

### Formato 2: Com tags
```
[landing_page_url]https://seusite.com.br/pagina[/landing_page_url]
[objetivo_final]agendamentos[/objetivo_final]
[perfil_cliente]descrição da persona e suas dores[/perfil_cliente]
[formato_anuncio]Reels[/formato_anuncio]
[foco]liquidação de inverno[/foco]
```

## Descrição Detalhada dos Campos

| Campo                | Obrigatório | Descrição                                      | Exemplos                                                            |
| -------------------- | ----------- | ---------------------------------------------- | ------------------------------------------------------------------- |
| **landing_page_url** | ✅ Sim       | URL completa da página de destino              | `https://exemplo.com.br/produto`                                    |
| **objetivo_final**   | ✅ Sim       | Ação desejada do usuário                       | `contato`, `leads`, `vendas`, `agendamentos`, `downloads`           |
| **perfil_cliente**   | ✅ Sim       | Persona detalhada com idade, interesses, dores | `Mulheres 30-50 anos interessadas em bem-estar e qualidade de vida` |
| **formato_anuncio**  | ✅ Sim       | Formato do anúncio Instagram                   | `Reels`, `Stories`, `Feed`                                          |
| **foco**             | ❌ Não       | Tema/gancho específico da campanha             | `black friday`, `não engordar no inverno`, `volta às aulas`         |

## Como o Campo "foco" Funciona

### Quando USAR o campo "foco":
- Campanhas sazonais (inverno, verão, festas)
- Promoções específicas (liquidação, black friday)
- Benefícios direcionados (emagrecer para o verão, preparação para vestibular)
- Ganchos de urgência (últimas vagas, oferta limitada)

### O que o "foco" influencia:
- **Headlines**: Direcionadas ao tema específico
- **Corpo do texto**: Mensagens alinhadas ao gancho
- **CTAs**: Calls-to-action contextualizadas
- **Descrição visual**: Elementos visuais relacionados ao tema
- **Coerência**: Todas as 3 variações mantêm o tema consistente

### Importante sobre o "foco":
- É **opcional** - sem ele, o sistema funciona normalmente
- Não aparece no JSON final (usado apenas para guiar a geração)
- Ajuda a criar campanhas mais direcionadas e coerentes
- Mantém alinhamento com a landing page enquanto enfatiza o tema

## Exemplos Práticos

### Exemplo 1: Clínica de Saúde (sem foco)
```
landing_page_url: https://clinicasaude.com.br/consulta
objetivo_final: agendamentos de consultas
perfil_cliente: Pessoas acima de 40 anos preocupadas com saúde preventiva, classe B/C
formato_anuncio: Feed
```

### Exemplo 2: Nutricionista (com foco sazonal)
```
landing_page_url: https://nutrologodivinopolis.com.br/masculino/
objetivo_final: agendamentos de consulta via WhatsApp
perfil_cliente: homens 35-50 anos, executivos com sobrepeso, querem emagrecer sem perder massa muscular
formato_anuncio: Reels
foco: não engordar no inverno
```

### Exemplo 3: E-commerce (com foco promocional)
```
landing_page_url: https://loja.exemplo.com.br/categoria/roupas
objetivo_final: vendas
perfil_cliente: mulheres 25-40 anos, mães modernas que buscam praticidade e estilo
formato_anuncio: Stories
foco: liquidação de inverno 70% off
```

### Exemplo 4: Curso Online (com foco de urgência)
```
landing_page_url: https://curso.exemplo.com.br/inscricao
objetivo_final: leads qualificados
perfil_cliente: jovens 18-25 anos querendo primeira oportunidade no mercado tech
formato_anuncio: Reels
foco: últimas vagas turma janeiro
```

## Saída Esperada

O sistema gerará **3 variações de anúncio** em formato JSON, cada uma contendo:

### Estrutura do JSON de Saída
- **landing_page_url**: URL fornecida
- **formato**: Formato escolhido (Reels/Stories/Feed)
- **copy**:
  - headline: Título principal (máx 40 caracteres)
  - corpo: Texto do anúncio (máx 125 caracteres)
  - cta_texto: Texto do botão
- **visual**:
  - descricao_imagem: Descrição detalhada da imagem
  - aspect_ratio: Proporção da imagem (9:16, 1:1, 4:5, 16:9)
- **cta_instagram**: Tipo de CTA (Saiba mais, Enviar mensagem, etc.)
- **fluxo**: Jornada do usuário
- **referencia_padroes**: Padrões de alta performance utilizados
- **contexto_landing**: Elementos extraídos da landing page

### Características das Variações:
1. **Todas respeitam** o formato escolhido
2. **Todas se alinham** ao objetivo e perfil
3. **Se houver foco**, todas mantêm o tema consistente
4. **Cada uma explora** ângulos diferentes do mesmo conceito

## Notas Importantes

1. **StoryBrand Automático**: O sistema analisa automaticamente a landing page usando o framework StoryBrand
2. **Extração Real**: O conteúdo é extraído diretamente do HTML da página (não apenas meta tags)
3. **Validação Rigorosa**: Todas as saídas passam por múltiplas validações
4. **Conformidade Instagram**: Respeita políticas e melhores práticas da plataforma
5. **Otimização LLM**: Usa Gemini 2.5 para análise semântica profunda

## Troubleshooting

### Erro: "Campo obrigatório faltando"
- Verifique se incluiu todos os 4 campos obrigatórios
- Use o formato exato dos nomes dos campos

### Erro: "Formato inválido"
- Formato deve ser exatamente: `Reels`, `Stories` ou `Feed` (case sensitive)

### Página não carrega
- Verifique se a URL está acessível publicamente
- Algumas páginas com proteção anti-bot podem falhar

### Foco não aplicado
- Certifique-se de que o foco está alinhado com o conteúdo da landing page
- Foco muito específico pode ser adaptado para manter coerência

---

**Última atualização**: 2025-09-14
**Versão**: 3.0.0 (Adicionado suporte ao campo "foco")