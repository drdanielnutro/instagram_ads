#!/usr/bin/env python3
"""
Script de teste para validar as refatorações do sistema de anúncios
"""

import asyncio
import json
from google.adk.invocation_context import session_maker
from app.agent import complete_pipeline

async def test_ad_generation():
    """Testa a geração de anúncios com o sistema refatorado"""
    
    # Caso de teste com todos os novos campos
    test_input = """
    landing_page_url: https://clinicasaude.com.br
    objetivo_final: agendamentos
    perfil_cliente: Mulheres 30-50 anos, classe B, preocupadas com saúde preventiva
    formato_anuncio: Feed
    """
    
    print("=" * 60)
    print("TESTE DO SISTEMA REFATORADO")
    print("=" * 60)
    print(f"Entrada de teste:\n{test_input}")
    print("=" * 60)
    
    try:
        # Criar sessão e executar pipeline
        async with session_maker() as session:
            result = await complete_pipeline.run(
                ctx=session,
                input_text=test_input
            )
            
            # Verificar resultado
            if result and hasattr(result, 'output'):
                output = result.output
                print("\n✅ RESULTADO OBTIDO:")
                print("-" * 60)
                
                # Tentar parsear como JSON
                try:
                    if isinstance(output, str):
                        ads_json = json.loads(output)
                    else:
                        ads_json = output
                    
                    print(json.dumps(ads_json, indent=2, ensure_ascii=False))
                    
                    # Validações
                    print("\n📊 VALIDAÇÕES:")
                    print("-" * 60)
                    
                    if isinstance(ads_json, list):
                        print(f"✓ Número de variações: {len(ads_json)}")
                        
                        for i, ad in enumerate(ads_json, 1):
                            print(f"\nVariação {i}:")
                            print(f"  - Formato: {ad.get('formato', 'N/A')}")
                            print(f"  - Tem contexto_landing: {'✓' if 'contexto_landing' in ad else '✗'}")
                            print(f"  - Tem descricao_imagem: {'✓' if ad.get('visual', {}).get('descricao_imagem') else '✗'}")
                            print(f"  - Tem prompt_estado_atual: {'✓' if ad.get('visual', {}).get('prompt_estado_atual') else '✗'}")
                            print(f"  - Tem prompt_estado_aspiracional: {'✓' if ad.get('visual', {}).get('prompt_estado_aspiracional') else '✗'}")
                            print(f"  - Sem duração: {'✓' if 'duracao' not in ad.get('visual', {}) else '✗'}")
                    else:
                        print("⚠️ Resultado não é uma lista")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Erro ao parsear JSON: {e}")
                    print(f"Output raw: {output}")
            else:
                print("❌ Nenhum resultado obtido do pipeline")
                
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Iniciando teste do sistema refatorado...")
    asyncio.run(test_ad_generation())
