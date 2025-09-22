# Diagnóstico do Preview de Anúncios

- **Problema identificado:** incompatibilidade de estrutura de dados entre o backend (campos individuais `image_estado_*_url`) e o frontend (espera `visual.images`).
- **Evidências:** artefatos em `artifacts/ads_final/*.json` apresentam apenas os campos individuais de URL, sem o array `images[]`.
