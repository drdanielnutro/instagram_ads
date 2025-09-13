
# Formato de Entrada para Geração de Anúncios Instagram

## Campos Principais (OBRIGATÓRIOS)

### Opção 1: Formato com tags
```
[landing_page_url]https://seusite.com.br[/landing_page_url]
[objetivo_final]gerar leads qualificados[/objetivo_final]
[perfil_cliente]Empreendedores de 25-45 anos que buscam crescer seu negócio online[/perfil_cliente]
```

### Opção 2: Formato chave-valor (mais simples)
```
landing_page_url: https://seusite.com.br
objetivo_final: gerar leads qualificados
perfil_cliente: Empreendedores de 25-45 anos que buscam crescer seu negócio online
```

## Descrição dos Campos

| Campo | Descrição | Exemplos |
|-------|-----------|----------|
| **landing_page_url** | URL da página de destino do anúncio | `https://exemplo.com.br` |
| **objetivo_final** | O que você quer alcançar com o anúncio | `contato`, `leads`, `vendas`, `agendamentos` |
| **perfil_cliente** | Descrição detalhada da persona/público-alvo | `Mulheres 30-50 anos interessadas em bem-estar` |

## Exemplo Completo de Prompt

```
landing_page_url: https://clinicasaude.com.br/consulta
objetivo_final: agendamentos de consultas
perfil_cliente: Pessoas acima de 40 anos preocupadas com saúde preventiva, classe B/C, que valorizam atendimento humanizado
```

## Saída Esperada

O agente irá gerar um JSON completo com:
- Copy (headline, corpo, CTA)
- Visual (descrição, aspect ratio, duração)
- Formato (Reels, Stories, Feed)
- Fluxo de conversão
- Referências de padrões de alta performance