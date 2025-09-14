#!/usr/bin/env python3
"""
Teste da ferramenta web_fetch_tool
Testa apenas a capacidade de buscar e extrair conteúdo de URLs
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Adicionar o diretório app ao path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

# Importar a ferramenta
from tools.web_fetch import web_fetch_tool


# Mock do ToolContext
class MockToolContext:
    """Context simulado para a ferramenta web_fetch"""
    def __init__(self):
        self.state = {}


def test_web_fetch(url: str) -> Dict[str, Any]:
    """
    Testa a ferramenta web_fetch_tool com uma URL.

    Args:
        url: URL para testar

    Returns:
        Resultado do fetch
    """

    print("=" * 70)
    print("TESTE DA FERRAMENTA WEB_FETCH")
    print("=" * 70)
    print(f"\n🌐 URL: {url}")
    print("-" * 70)

    # Criar contexto mock
    context = MockToolContext()

    try:
        print("\n📥 Iniciando fetch...")

        # Chamar a ferramenta
        result = web_fetch_tool(url, context)

        # Analisar resultado
        status = result.get('status')

        if status == 'success':
            print("✅ Fetch realizado com sucesso!\n")

            # Informações básicas
            print("📊 INFORMAÇÕES EXTRAÍDAS:")
            print("-" * 40)

            # Título
            title = result.get('title', 'N/A')
            print(f"📌 Título: {title[:100]}")

            # Meta descrição
            meta = result.get('meta_description', 'N/A')
            if meta:
                print(f"📝 Meta Descrição: {meta[:150]}...")

            # Tamanhos
            html_size = len(result.get('html_content', ''))
            text_size = len(result.get('text_content', ''))
            print(f"\n📦 Tamanhos:")
            print(f"   HTML: {html_size:,} caracteres")
            print(f"   Texto: {text_size:,} caracteres")

            # Metadados
            metadata = result.get('metadata', {})
            if metadata:
                print(f"\n🏷️ Metadados:")
                print(f"   URL final: {metadata.get('url', url)}")
                print(f"   Status HTTP: {metadata.get('status_code', 'N/A')}")

                # H1 headings
                h1s = metadata.get('h1_headings', [])
                if h1s:
                    print(f"   H1 títulos encontrados: {len(h1s)}")
                    for i, h1 in enumerate(h1s[:3], 1):
                        print(f"     {i}. {h1[:80]}...")

                # Open Graph
                og = metadata.get('open_graph', {})
                if og:
                    print(f"   Open Graph tags: {len(og)}")
                    if 'title' in og:
                        print(f"     - og:title: {og['title'][:80]}")
                    if 'description' in og:
                        print(f"     - og:description: {og['description'][:80]}...")
                    if 'image' in og:
                        print(f"     - og:image: ✓")

            # Amostra do texto
            text = result.get('text_content', '')
            if text:
                print(f"\n📄 AMOSTRA DO TEXTO EXTRAÍDO:")
                print("-" * 40)
                # Primeiras 500 caracteres
                sample = text[:500].replace('\n\n', '\n')
                print(sample)
                if len(text) > 500:
                    print("...")
                print("-" * 40)

            # Verificar estado salvo
            if hasattr(context, 'state') and context.state:
                print(f"\n💾 Estado salvo no contexto:")
                print(f"   last_fetched_url: {context.state.get('last_fetched_url', 'N/A')}")
                print(f"   last_fetch_status: {context.state.get('last_fetch_status', 'N/A')}")

            # Salvar resultado completo
            output_file = Path(__file__).parent / 'test_web_fetch_result.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                # Salvar apenas metadados (não o HTML completo para economizar espaço)
                save_data = {
                    'url': url,
                    'status': status,
                    'title': title,
                    'meta_description': meta,
                    'html_size': html_size,
                    'text_size': text_size,
                    'metadata': metadata,
                    'text_sample': text[:1000] if text else None
                }
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            print(f"\n💾 Resultado salvo em: {output_file}")

        else:
            # Erro no fetch
            error = result.get('error_message', 'Erro desconhecido')
            print(f"❌ Erro no fetch: {error}")

            # Detalhes do erro
            print(f"\n🔍 Detalhes:")
            print(f"   Status: {status}")
            print(f"   Mensagem: {error}")

            # Verificar se há metadados mesmo com erro
            metadata = result.get('metadata', {})
            if metadata:
                print(f"   Metadados disponíveis: {list(metadata.keys())}")

        return result

    except Exception as e:
        print(f"\n❌ Erro durante execução: {str(e)}")

        import traceback
        print("\nTraceback completo:")
        traceback.print_exc()

        return {
            'status': 'error',
            'error_message': str(e)
        }


def main():
    """Função principal para execução via linha de comando"""

    if len(sys.argv) < 2:
        print("USO: python test_web_fetch.py <URL>")
        print("\nExemplos:")
        print("  python test_web_fetch.py https://example.com")
        print("  python test_web_fetch.py https://www.google.com")
        print("\nURLs sugeridas para teste:")
        print("  - https://example.com (site simples)")
        print("  - https://www.wikipedia.org (conteúdo rico)")
        print("  - https://httpstat.us/200 (teste de status)")
        print("  - https://httpstat.us/404 (teste de erro)")
        sys.exit(1)

    url = sys.argv[1]

    # Validar URL básica
    if not url.startswith(('http://', 'https://')):
        print(f"❌ URL inválida: {url}")
        print("   A URL deve começar com http:// ou https://")
        sys.exit(1)

    # Executar teste
    result = test_web_fetch(url)

    # Código de saída baseado no resultado
    if result.get('status') == 'success':
        print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")
        sys.exit(0)
    else:
        print("\n⚠️  TESTE CONCLUÍDO COM ERRO")
        sys.exit(1)


if __name__ == "__main__":
    main()