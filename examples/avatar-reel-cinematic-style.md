# Exemplo — Diagnóstico de estilo cinematográfico

Saída real do `/watch` rodado num reel do Instagram com o intent
"estilo cinematográfico e linguagem de câmera".

- **Link:** https://www.instagram.com/reels/DM1Gp85OYtD/
- **Fonte:** re-edit vertical de footage de **Avatar (James Cameron / Wētā FX)** — provavelmente *Avatar: Fire and Ash* misturado com *The Way of Water* (clã das cinzas com pintura branca-e-vermelha, Na'vi, Pandora, "águas-vivas" voadoras, porta-aviões). Conta `cineprimecinemas` (página de cinema). O estilo é **do filme**, recortado num reel — não cinematografia original do autor do post.
- **Duração:** 02:30 · sem captions/transcript.

## Perfil editorial (medido pelo claude-watch)

- **Shots:** 48 · **Cuts/min:** 19,2 · **shot médio 3,13s / mediano 1,81s** → montagem de trailer (corte rápido, com planos-herói longos puxando a média pra cima).
- **Motion** (0-1, relativo): média **0,49**, **pico 1,0 @ 01:55** (clímax de fogo/batalha).
- **Câmera:** predominantemente **estática** (19× static, 14× handheld, 4× tilt-up, 4× tilt-down, 4× pan-left, 3× pan-right) — quase **zero zoom**. Wides épicos travados + handheld pra ação/intimidade.

## Linguagem visual (inferida dos frames)

- CG fotorrealista (Wētā), **paleta bioluminescente**: teal/azul Na'vi × acentos quentes (fogo, pintura de guerra) — teal-and-orange *motivado* por luz, não filtro.
- **Atmosfera volumétrica** (god rays, névoa, fumaça); forte perspectiva atmosférica.
- **Alternância de escala**: estabelecedores épicos em wide × close-ups íntimos de rosto (subsurface scattering na pele).
- **Luz naturalista motivada** (fogueira, cáusticas subaquáticas, céu difuso, bioluminescência).
- **DOF rasa** nos closes / **foco profundo** nas paisagens; ângulos baixos heroicos; enquadramento centrado.

## Tratamento do reel (edição)

- Recorte **9:16 vertical** de footage scope 2.39:1 → enquadramento fechado, rosto ao centro.
- **Supercut de trailer**: abre contemplativo (Pandora) → beats de personagem → crescendo de ação/fogo (~1:55).

## Limites do diagnóstico

- Grading/LUT, lente e profundidade de campo são **inferidos dos frames, não medidos**.
- **Sem áudio analisado** (sem captions/Whisper) — nenhum comentário sobre música/sound design.
- Sentido de pan/tilt é heurístico (confiável pro **eixo**, não pro sentido).

---

Reproduzir:

```bash
python3 scripts/watch.py "https://www.instagram.com/reels/DM1Gp85OYtD/" \
  --no-whisper --intent "estilo cinematográfico e linguagem de câmera"
```
