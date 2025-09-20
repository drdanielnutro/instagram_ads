#!/usr/bin/env python3
"""
Script de teste simples para geração de imagem via Gemini
Objetivo: Entender o que o modelo retorna exatamente
"""

import os
import sys
from google import genai
from google.genai import types
import json
from io import BytesIO
from PIL import Image

# Configuração
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "instagram-ads-472021")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

print(f"🔧 Configuração:")
print(f"   Project: {PROJECT_ID}")
print(f"   Location: {LOCATION}")

# Cliente Gemini
client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
)

def test_simple_image_generation():
    """Testa geração de uma única imagem"""
    print("\n🎨 Teste 1: Geração simples de imagem")
    print("-" * 50)

    # Prompt simples
    prompt = "Gere uma imagem de uma mulher de 40 anos olhando frustrada para a balança, em um quarto bem iluminado"

    print(f"📝 Prompt: {prompt}")

    # Configuração da requisição
    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        temperature=0.9,
        top_p=0.95,
        max_output_tokens=32768,
        system_instruction=[types.Part.from_text(
            text="Você é um gerador de imagens fotorrealistas para anúncios."
        )],
    )

    # Conteúdo da requisição
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )
    ]

    print("📤 Enviando requisição ao Gemini...")

    try:
        # Chamada ao modelo
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=contents,
            config=config,
        )

        print("✅ Resposta recebida!")

        # Analisar estrutura da resposta
        print("\n🔍 Estrutura da resposta:")
        print(f"   Type: {type(response)}")
        print(f"   Attributes: {dir(response)}")

        if hasattr(response, 'candidates'):
            print(f"   Candidates count: {len(response.candidates)}")

            for i, candidate in enumerate(response.candidates):
                print(f"\n   Candidate {i}:")
                print(f"      Has content: {hasattr(candidate, 'content')}")

                if hasattr(candidate, 'content'):
                    content = candidate.content
                    print(f"      Content type: {type(content)}")
                    print(f"      Has parts: {hasattr(content, 'parts')}")

                    if hasattr(content, 'parts'):
                        print(f"      Parts count: {len(content.parts)}")

                        for j, part in enumerate(content.parts):
                            print(f"\n      Part {j}:")
                            print(f"         Type: {type(part)}")
                            print(f"         Attributes: {[attr for attr in dir(part) if not attr.startswith('_')]}")

                            # Verificar se tem texto
                            if hasattr(part, 'text') and part.text:
                                print(f"         Has text: Yes ({len(part.text)} chars)")
                                print(f"         Text preview: {part.text[:100]}...")

                            # Verificar se tem inline_data (imagem)
                            if hasattr(part, 'inline_data'):
                                inline_data = part.inline_data
                                print(f"         Has inline_data: Yes")
                                print(f"         Inline data type: {type(inline_data)}")

                                if hasattr(inline_data, 'data'):
                                    data = inline_data.data
                                    print(f"         Data type: {type(data)}")
                                    print(f"         Data length: {len(data)} bytes")

                                    # Tentar salvar a imagem
                                    try:
                                        with BytesIO(data) as buffer:
                                            img = Image.open(buffer)
                                            img_rgb = img.convert("RGB")
                                            output_path = "test_image_output.jpg"
                                            img_rgb.save(output_path, "JPEG")
                                            print(f"         ✅ Imagem salva em: {output_path}")
                                            print(f"         Dimensões: {img_rgb.size}")
                                    except Exception as e:
                                        print(f"         ❌ Erro ao salvar imagem: {e}")

                                if hasattr(inline_data, 'mime_type'):
                                    print(f"         MIME type: {inline_data.mime_type}")

        # Tentar extrair com to_json se disponível
        if hasattr(response, 'to_json'):
            print("\n📊 JSON da resposta (primeiros 500 chars):")
            json_str = response.to_json()
            print(json_str[:500])

        return response

    except Exception as e:
        print(f"❌ Erro na geração: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("\n🚀 Iniciando teste de geração de imagem")
    print("=" * 60)

    response = test_simple_image_generation()

    if response:
        print("\n✅ Teste concluído com sucesso!")
    else:
        print("\n❌ Teste falhou")

    print("\n" + "=" * 60)