#!/usr/bin/env python3
"""Testa se try_parse_json_string consegue converter json_baixado em json_copiado_chat"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa diretamente a função, evitando imports do ADK
def _strip_markdown_fence(value: str) -> str:
    """Remove Markdown fences (```json ... ```), preserving inner JSON."""
    text = value.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if not lines:
        return ""

    # Drop opening fence (``` or ```json)
    if lines[0].startswith("```"):
        lines = lines[1:]

    # Drop closing fence(s)
    while lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()

def try_parse_json_string(raw: str) -> tuple[bool, any]:
    """Attempt to parse a JSON string that may be wrapped in Markdown fences."""
    if not isinstance(raw, str):
        return False, raw

    stripped = _strip_markdown_fence(raw)
    if not stripped:
        return False, raw

    try:
        return True, json.loads(stripped)
    except json.JSONDecodeError:
        return False, raw

# Lê o arquivo json_baixado.json (que está envolto em string com markdown)
with open("json_baixado.json", "r", encoding="utf-8") as f:
    content_raw = f.read()
    # Remove as aspas externas que envolvem tudo
    content = json.loads(content_raw)

print("Conteúdo original (primeiros 100 chars):")
print(content[:100])
print()

# Tenta fazer o parse
success, parsed_data = try_parse_json_string(content)

print(f"Parse bem-sucedido: {success}")
print()

if success:
    # Salva o resultado parseado
    with open("json_parseado_teste.json", "w", encoding="utf-8") as f:
        json.dump(parsed_data, f, ensure_ascii=False, indent=2)

    print("JSON parseado salvo em: json_parseado_teste.json")
    print(f"Tipo do resultado: {type(parsed_data)}")
    print(f"Número de variações: {len(parsed_data) if isinstance(parsed_data, list) else 'N/A'}")

    # Compara com o json_copiado_chat.json
    with open("json_copiado_chat.json", "r", encoding="utf-8") as f:
        expected = json.load(f)

    print(f"\nComparação:")
    print(f"Parseado == Esperado: {parsed_data == expected}")
else:
    print("Falha no parse!")
    print(f"Conteúdo retornado: {parsed_data[:200] if isinstance(parsed_data, str) else parsed_data}")