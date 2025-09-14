#!/usr/bin/env python3
"""
Teste direto do StoryBrandExtractor com LangExtract
Executa extração de elementos StoryBrand de uma página HTML de exemplo
"""

import os
import sys
import json
from pathlib import Path

# Adicionar o diretório app ao path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

# Importar o extrator
from tools.langextract_sb7 import StoryBrandExtractor

def test_with_example_html():
    """Testa com HTML de exemplo embutido"""

    # HTML de exemplo de uma landing page fictícia
    example_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Transforme seu Negócio Digital - Agência Growth</title>
        <meta name="description" content="Ajudamos empresários a escalar suas vendas online">
    </head>
    <body>
        <header>
            <h1>Seu negócio está perdendo vendas online?</h1>
            <p>Sabemos como é frustrante ver concorrentes vendendo mais enquanto você luta para conseguir clientes.</p>
        </header>

        <section class="problema">
            <h2>O Problema que Você Enfrenta</h2>
            <p>Você trabalha duro mas não consegue converter visitantes em clientes.</p>
            <p>Se sente perdido com tantas estratégias de marketing que não funcionam.</p>
            <p>É injusto que empresas menores estejam crescendo mais rápido que a sua.</p>
        </section>

        <section class="sobre">
            <h2>Por que Somos Diferentes</h2>
            <p>Com 10 anos de experiência, já ajudamos mais de 500 empresas a triplicar suas vendas.</p>
            <p>Entendemos sua frustração porque já passamos por isso.</p>
            <div class="testimonial">
                "A Agência Growth transformou nosso negócio. Triplicamos o faturamento em 6 meses!" - João Silva, CEO TechStart
            </div>
        </section>

        <section class="plano">
            <h2>Nosso Plano Simples de 3 Passos</h2>
            <ol>
                <li>Análise gratuita do seu negócio digital</li>
                <li>Estratégia personalizada de crescimento</li>
                <li>Implementação com acompanhamento semanal</li>
            </ol>
        </section>

        <section class="cta">
            <button class="primary">Agende Sua Consulta Gratuita Agora</button>
            <a href="/ebook" class="secondary">Baixe nosso guia gratuito de vendas online</a>
        </section>

        <section class="urgencia">
            <h2>Não Deixe Para Depois</h2>
            <p>Cada dia sem uma estratégia digital é dinheiro perdido.</p>
            <p>Seus concorrentes não vão esperar você decidir.</p>
        </section>

        <section class="transformacao">
            <h2>Imagine Seu Negócio Daqui a 6 Meses</h2>
            <p>Vendas automáticas acontecendo 24/7</p>
            <p>Clientes chegando sem você precisar prospectar</p>
            <p>Liberdade para focar no que você ama fazer</p>
        </section>
    </body>
    </html>
    """

    print("=" * 60)
    print("TESTE DO STORYBRAND EXTRACTOR COM LANGEXTRACT")
    print("=" * 60)

    # Configurar para usar Vertex AI
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"

    if use_vertex:
        print("\n🌩️  Usando Vertex AI")
        print(f"   Projeto: {os.getenv('GOOGLE_CLOUD_PROJECT', 'não configurado')}")
        print(f"   Região: {os.getenv('GOOGLE_CLOUD_LOCATION', 'não configurado')}")

        # Verificar se ADC está configurado
        import subprocess
        try:
            result = subprocess.run(
                ["gcloud", "auth", "application-default", "print-access-token"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print("✅ Application Default Credentials configurado")
                api_key = None  # Vertex AI não usa API key
            else:
                print("❌ ADC não configurado. Execute: gcloud auth application-default login")
                print(f"   Erro: {result.stderr}")
                return
        except subprocess.TimeoutExpired:
            # Se demorou, provavelmente está funcionando mas lento
            print("⚠️  Verificação ADC demorou, mas provavelmente está configurado")
            print("   Tentando continuar...")
            api_key = None
        except Exception as e:
            print(f"⚠️  Erro ao verificar ADC: {e}")
            # Tentar continuar mesmo assim
            print("   Tentando continuar...")
            api_key = None
    else:
        # Verificar API key para Gemini direto
        api_key = os.getenv("LANGEXTRACT_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
        if not api_key:
            print("\n⚠️  AVISO: Nenhuma API key encontrada!")
            print("Configure uma das seguintes variáveis de ambiente:")
            print("  - LANGEXTRACT_API_KEY")
            print("  - GOOGLE_GENAI_API_KEY")
            print("\nPara configurar temporariamente:")
            print("  export GOOGLE_GENAI_API_KEY='sua-chave-aqui'")
            return

        print(f"\n✅ API Key configurada: {api_key[:10]}...")

    try:
        # Criar instância do extrator
        print("\n📦 Inicializando StoryBrandExtractor...")
        extractor = StoryBrandExtractor(
            model_id="gemini-2.5-flash-lite",  # Usando gemini 2.5 flash lite
            api_key=api_key
        )
        print("✅ Extrator inicializado com sucesso")

        # Executar extração
        print("\n🔍 Iniciando extração dos elementos StoryBrand...")
        print("   (isso pode levar alguns segundos...)")

        result = extractor.extract(example_html)

        # Exibir resultados
        print("\n" + "=" * 60)
        print("RESULTADOS DA EXTRAÇÃO")
        print("=" * 60)

        # Score de completude
        score = result.get('completeness_score', 0)
        print(f"\n📊 Score de Completude: {score:.0%}")
        print(f"   Elementos encontrados: {len(result.get('metadata', {}).get('elements_found', []))}/7")

        # 1. Character (Personagem)
        print("\n1️⃣ CHARACTER (Cliente Ideal):")
        character = result.get('character', {})
        if character.get('description'):
            print(f"   Descrição: {character['description']}")
            if character.get('evidence'):
                print(f"   Evidência: '{character['evidence'][0]}'")
            print(f"   Confiança: {character.get('confidence', 0):.0%}")
        else:
            print("   ❌ Não encontrado")

        # 2. Problem (Problema)
        print("\n2️⃣ PROBLEM (Problemas):")
        problem = result.get('problem', {})
        types = problem.get('types', {})
        if types.get('external'):
            print(f"   Externo: {types['external']}")
        if types.get('internal'):
            print(f"   Interno: {types['internal']}")
        if types.get('philosophical'):
            print(f"   Filosófico: {types['philosophical']}")
        if not any(types.values()):
            print("   ❌ Não encontrado")

        # 3. Guide (Guia)
        print("\n3️⃣ GUIDE (Marca como Guia):")
        guide = result.get('guide', {})
        if guide.get('authority'):
            print(f"   Autoridade: {guide['authority']}")
        if guide.get('empathy'):
            print(f"   Empatia: {guide['empathy']}")
        if not (guide.get('authority') or guide.get('empathy')):
            print("   ❌ Não encontrado")

        # 4. Plan (Plano)
        print("\n4️⃣ PLAN (Plano de Ação):")
        plan = result.get('plan', {})
        if plan.get('steps'):
            print(f"   Passos encontrados: {len(plan['steps'])}")
            for i, step in enumerate(plan['steps'], 1):
                print(f"   {i}. {step}")
        else:
            print("   ❌ Não encontrado")

        # 5. Action (Ação)
        print("\n5️⃣ ACTION (Chamadas para Ação):")
        action = result.get('action', {})
        if action.get('primary'):
            print(f"   CTA Primário: {action['primary']}")
        if action.get('secondary'):
            print(f"   CTA Secundário: {action['secondary']}")
        if not (action.get('primary') or action.get('secondary')):
            print("   ❌ Não encontrado")

        # 6. Failure (Fracasso)
        print("\n6️⃣ FAILURE (Consequências de Não Agir):")
        failure = result.get('failure', {})
        if failure.get('consequences'):
            for cons in failure['consequences']:
                print(f"   - {cons}")
        else:
            print("   ❌ Não encontrado")

        # 7. Success (Sucesso)
        print("\n7️⃣ SUCCESS (Transformação):")
        success = result.get('success', {})
        if success.get('transformation'):
            print(f"   Transformação: {success['transformation']}")
        if success.get('benefits'):
            print(f"   Benefícios:")
            for benefit in success['benefits']:
                print(f"   - {benefit}")
        if not (success.get('transformation') or success.get('benefits')):
            print("   ❌ Não encontrado")

        # Metadados
        print("\n" + "=" * 60)
        print("METADADOS")
        print("=" * 60)
        metadata = result.get('metadata', {})
        print(f"Método: {metadata.get('extraction_method', 'unknown')}")
        print(f"Modelo: {metadata.get('model_used', 'unknown')}")
        print(f"Total de extrações: {metadata.get('total_extractions', 0)}")

        # Salvar resultado completo
        output_file = Path(__file__).parent / 'test_langextract_result.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Resultado completo salvo em: {output_file}")

        # Tentar gerar visualização HTML
        try:
            print("\n🎨 Tentando gerar visualização HTML...")
            html_file = extractor.save_visualization(result, str(Path(__file__).parent))
            if html_file:
                print(f"✅ Visualização salva em: {html_file}")
        except Exception as e:
            print(f"⚠️  Não foi possível gerar visualização: {e}")

        print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")

    except ImportError as e:
        print(f"\n❌ Erro de importação: {e}")
        print("\nVerifique se langextract está instalado:")
        print("  pip install langextract")

    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        import traceback
        print("\nTraceback completo:")
        traceback.print_exc()


def test_with_url(url: str):
    """Testa com uma URL real"""

    print(f"\n🌐 Testando com URL: {url}")

    try:
        # Importar web_fetch para obter HTML real
        from tools.web_fetch import web_fetch_tool
        from google.adk.context import ToolContext

        # Criar contexto mock
        context = ToolContext()

        # Buscar HTML
        print("📥 Baixando conteúdo da página...")
        result = web_fetch_tool(url, context)

        if result['status'] != 'success':
            print(f"❌ Erro ao buscar URL: {result.get('error')}")
            return

        html_content = result['html_content']
        print(f"✅ HTML obtido: {len(html_content)} caracteres")

        # Extrair StoryBrand
        api_key = os.getenv("LANGEXTRACT_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
        if not api_key:
            print("❌ API key não configurada")
            return

        extractor = StoryBrandExtractor(api_key=api_key)
        print("\n🔍 Extraindo elementos StoryBrand...")

        sb_result = extractor.extract(html_content)

        # Mostrar resultados resumidos
        print(f"\n📊 Score: {sb_result['completeness_score']:.0%}")
        print(f"Elementos encontrados: {', '.join(sb_result['metadata']['elements_found'])}")

    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Se passou URL como argumento
        test_with_url(sys.argv[1])
    else:
        # Teste com HTML de exemplo
        test_with_example_html()

        print("\n" + "=" * 60)
        print("💡 DICA: Você também pode testar com uma URL real:")
        print(f"   python {sys.argv[0]} https://exemplo.com")
        print("=" * 60)