#!/usr/bin/env python3
"""
Teste completo do pipeline: URL → HTML → StoryBrand
Extrai conteúdo de uma URL real e aplica análise StoryBrand
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Adicionar o diretório app ao path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Importar as ferramentas necessárias
from tools.web_fetch import web_fetch_tool
from tools.langextract_sb7 import StoryBrandExtractor

# Mock do ToolContext para web_fetch_tool
class MockToolContext:
    """Context simulado para a ferramenta web_fetch"""
    def __init__(self):
        self.state = {}
        self.messages = []

    def set_state(self, key: str, value: Any):
        self.state[key] = value

    def get_state(self, key: str, default=None):
        return self.state.get(key, default)

    def add_message(self, message: str):
        self.messages.append(message)


def test_url_to_storybrand(url: str) -> Dict[str, Any]:
    """
    Testa o pipeline completo de extração StoryBrand de uma URL.

    Args:
        url: URL da landing page para analisar

    Returns:
        Dicionário com os resultados da análise
    """

    print("=" * 70)
    print("TESTE COMPLETO: URL → HTML → STORYBRAND")
    print("=" * 70)
    print(f"\n🌐 URL: {url}")

    # Verificar configuração do Vertex AI
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
    if use_vertex:
        print(f"\n🌩️  Usando Vertex AI")
        print(f"   Projeto: {os.getenv('GOOGLE_CLOUD_PROJECT', 'não configurado')}")
        print(f"   Região: {os.getenv('GOOGLE_CLOUD_LOCATION', 'não configurado')}")

    results = {
        "url": url,
        "web_fetch": {},
        "storybrand": {},
        "errors": []
    }

    try:
        # PASSO 1: Buscar conteúdo HTML da URL
        print("\n" + "=" * 50)
        print("PASSO 1: BUSCANDO CONTEÚDO DA URL")
        print("=" * 50)

        # Criar contexto mock para web_fetch_tool
        context = MockToolContext()

        print("📥 Fazendo download do HTML...")
        fetch_result = web_fetch_tool(url, context)

        if fetch_result['status'] != 'success':
            error_msg = f"Erro ao buscar URL: {fetch_result.get('error', 'Unknown error')}"
            print(f"❌ {error_msg}")
            results['errors'].append(error_msg)
            return results

        html_content = fetch_result.get('html_content', '')
        text_content = fetch_result.get('text_content', '')

        print(f"✅ HTML obtido com sucesso!")
        print(f"   Tamanho HTML: {len(html_content):,} caracteres")
        print(f"   Tamanho texto: {len(text_content):,} caracteres")
        print(f"   Título: {fetch_result.get('title', 'N/A')}")
        print(f"   Descrição: {fetch_result.get('meta_description', 'N/A')[:100]}...")

        results['web_fetch'] = {
            'status': 'success',
            'html_size': len(html_content),
            'text_size': len(text_content),
            'title': fetch_result.get('title'),
            'meta_description': fetch_result.get('meta_description'),
            'metadata': fetch_result.get('metadata', {})
        }

        # PASSO 2: Aplicar análise StoryBrand
        print("\n" + "=" * 50)
        print("PASSO 2: ANÁLISE STORYBRAND")
        print("=" * 50)

        print("🔍 Inicializando extrator StoryBrand...")
        extractor = StoryBrandExtractor()
        print(f"   Modelo: {extractor.model_id}")
        print(f"   Modo: {'Vertex AI' if extractor.use_vertex else 'Gemini API'}")

        print("\n📊 Extraindo elementos StoryBrand...")
        print("   (isso pode levar 10-30 segundos...)")

        storybrand_result = extractor.extract(html_content)

        # Analisar resultados
        score = storybrand_result.get('completeness_score', 0)
        elements_found = storybrand_result.get('metadata', {}).get('elements_found', [])

        print(f"\n✅ Análise concluída!")
        print(f"   Score de completude: {score:.0%}")
        print(f"   Elementos encontrados: {len(elements_found)}/7")

        results['storybrand'] = storybrand_result

        # PASSO 3: Exibir resultados detalhados
        print("\n" + "=" * 50)
        print("PASSO 3: RESULTADOS DETALHADOS")
        print("=" * 50)

        # 1. Character
        character = storybrand_result.get('character', {})
        print("\n1️⃣ CHARACTER (Cliente Ideal):")
        if character.get('description'):
            print(f"   ✓ {character['description']}")
            if character.get('evidence'):
                print(f"     Evidência: '{character['evidence'][0][:100]}...'")
        else:
            print("   ✗ Não identificado")

        # 2. Problem
        problem = storybrand_result.get('problem', {})
        types = problem.get('types', {})
        print("\n2️⃣ PROBLEM (Problemas):")
        if types.get('external'):
            print(f"   ✓ Externo: {types['external'][:100]}...")
        if types.get('internal'):
            print(f"   ✓ Interno: {types['internal'][:100]}...")
        if types.get('philosophical'):
            print(f"   ✓ Filosófico: {types['philosophical'][:100]}...")
        if not any(types.values()):
            print("   ✗ Não identificado")

        # 3. Guide
        guide = storybrand_result.get('guide', {})
        print("\n3️⃣ GUIDE (Marca como Guia):")
        if guide.get('authority'):
            print(f"   ✓ Autoridade: {guide['authority'][:100]}...")
        if guide.get('empathy'):
            print(f"   ✓ Empatia: {guide['empathy'][:100]}...")
        if not (guide.get('authority') or guide.get('empathy')):
            print("   ✗ Não identificado")

        # 4. Plan
        plan = storybrand_result.get('plan', {})
        print("\n4️⃣ PLAN (Plano de Ação):")
        if plan.get('steps'):
            print(f"   ✓ {len(plan['steps'])} passos identificados")
            for i, step in enumerate(plan['steps'][:3], 1):
                print(f"     {i}. {step[:80]}...")
        else:
            print("   ✗ Não identificado")

        # 5. Action
        action = storybrand_result.get('action', {})
        print("\n5️⃣ ACTION (Chamadas para Ação):")
        if action.get('primary'):
            print(f"   ✓ Primário: {action['primary']}")
        if action.get('secondary'):
            print(f"   ✓ Secundário: {action['secondary']}")
        if not (action.get('primary') or action.get('secondary')):
            print("   ✗ Não identificado")

        # 6. Failure
        failure = storybrand_result.get('failure', {})
        print("\n6️⃣ FAILURE (Consequências de Não Agir):")
        if failure.get('consequences'):
            print(f"   ✓ {len(failure['consequences'])} consequências identificadas")
            for cons in failure['consequences'][:2]:
                print(f"     - {cons[:80]}...")
        else:
            print("   ✗ Não identificado")

        # 7. Success
        success = storybrand_result.get('success', {})
        print("\n7️⃣ SUCCESS (Transformação):")
        if success.get('transformation'):
            print(f"   ✓ Transformação: {success['transformation']}")
        if success.get('benefits'):
            print(f"   ✓ {len(success['benefits'])} benefícios identificados")
            for benefit in success['benefits'][:2]:
                print(f"     - {benefit[:80]}...")
        if not (success.get('transformation') or success.get('benefits')):
            print("   ✗ Não identificado")

        # Salvar resultados em arquivo
        output_file = Path(__file__).parent / f'test_url_storybrand_result.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Resultados completos salvos em: {output_file}")

        # Resumo final
        print("\n" + "=" * 70)
        print("RESUMO DA ANÁLISE")
        print("=" * 70)
        print(f"✅ Pipeline executado com sucesso!")
        print(f"📊 Score StoryBrand: {score:.0%}")
        print(f"📝 Elementos encontrados: {', '.join(elements_found) if elements_found else 'Nenhum'}")

        if score >= 0.7:
            print("🎯 Excelente! A página tem uma narrativa StoryBrand bem estruturada.")
        elif score >= 0.5:
            print("⚠️  Bom, mas pode melhorar. Alguns elementos StoryBrand estão faltando.")
        else:
            print("❌ A página precisa de melhorias significativas na narrativa StoryBrand.")

    except Exception as e:
        error_msg = f"Erro durante execução: {str(e)}"
        print(f"\n❌ {error_msg}")
        results['errors'].append(error_msg)

        import traceback
        print("\nTraceback completo:")
        traceback.print_exc()

    return results


def main():
    """Função principal para execução via linha de comando"""

    if len(sys.argv) < 2:
        print("USO: python test_url_to_storybrand.py <URL>")
        print("\nExemplos:")
        print("  python test_url_to_storybrand.py https://example.com")
        print("  python test_url_to_storybrand.py https://landingpage.com/produto")
        print("\nURLs sugeridas para teste:")
        print("  - https://www.hubspot.com")
        print("  - https://www.salesforce.com")
        print("  - https://www.shopify.com")
        print("  - https://www.canva.com")
        sys.exit(1)

    url = sys.argv[1]

    # Validar URL básica
    if not url.startswith(('http://', 'https://')):
        print(f"❌ URL inválida: {url}")
        print("   A URL deve começar com http:// ou https://")
        sys.exit(1)

    # Executar teste
    results = test_url_to_storybrand(url)

    # Retornar código de saída baseado no sucesso
    if results.get('errors'):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()