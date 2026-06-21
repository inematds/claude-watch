# /watch

**Dê ao Claude a capacidade de assistir qualquer vídeo.**

> Cole uma URL ou um arquivo local e o Claude *assiste* — **extração de frames por corte de cena** (um frame por corte, não a cada N segundos), um **microscópio do hook 0-10s** (frames densos + Whisper word-level na abertura, onde todo vídeo ganha ou perde sua atenção), **métricas editoriais de pacing com motion por shot** e **auto-save opcional no Obsidian**, pra um vídeo assistido virar uma entrada conectada no wiki sem copia-e-cola.

Claude Code:
```
/plugin marketplace add inematds/claude-watch
/plugin install watch@claude-watch
```

claude.ai (web): [baixe o `watch.skill`](https://github.com/inematds/claude-watch/releases/latest) e solte em Settings → Capabilities → Skills.

Codex / skills genéricas:
```bash
git clone https://github.com/inematds/claude-watch.git ~/.codex/skills/watch
```

Zero config pra começar — `yt-dlp` e `ffmpeg` se instalam no primeiro run via `brew` no macOS (Linux/Windows imprimem os comandos exatos). Captions cobrem a maioria dos vídeos públicos de graça. Chave da API Whisper só é necessária quando o vídeo não tem legenda. Aponte `$WATCH_VAULT_DIR` pro seu vault Obsidian pra ligar o auto-save, ou deixe sem setar que a skill pula a etapa de ingest em silêncio.

## O que tem dentro

- **Extração de frames por corte de cena** — `scripts/frames.py` pega um frame por shot detectado via `select=gt(scene,...)` do ffmpeg, não um tick uniforme a cada N segundos. O custo de token fica plano em vídeo longo porque o número de frames é limitado pela quantidade de cortes, não pela duração.
- **Microscópio do hook 0-10s** — `scripts/hook.py` roda uma passada mais densa a 2 fps nos primeiros 10 segundos + um transcript Whisper word-level, pro relatório dizer o que estava na tela *conforme cada palavra caía*. Os 10 primeiros segundos são onde todo vídeo ganha ou perde sua atenção.
- **Métricas editoriais de pacing, motion e câmera** — `scripts/pacing.py` calcula cortes/min, duração média/mediana de shot, **motion por shot via ffmpeg `signalstats`** (delta de luma YDIF) e **movimento de câmera por shot** (pan / tilt / zoom / estático / handheld via ffmpeg `vidstabdetect`) — tudo sem opencv. O shot mais agitado também guia a escolha das hero frames. Dá pra raciocinar sobre ritmo como um editor faz.
- **`report.md` estruturado com marcadores de preenchimento** — `scripts/report.py` emite um relatório de esquema fixo (TL;DR, momentos-chave, breakdown do hook, perfil editorial, citações, entidades, conceitos, transcript) onde as seções narrativas são marcadores explícitos `<!-- pending Claude fill: ... -->`. O Claude tem uma lista de tarefas pra percorrer antes do ingest, não um doc em branco.
- **Auto-save opcional no Obsidian** — o Step 4.4 monta o relatório em `$VAULT_DIR/raw/watched/<slug>/` e abre via URL scheme `obsidian://`. O Step 4.5 oferece o ingest no wiki do vault. Os dois passos pulam limpo quando nenhum vault é detectado. O caminho do vault vem de `$WATCH_VAULT_DIR` ou é auto-detectado em `~/Second brain/`, `~/Documents/Obsidian/`, `~/Obsidian/`.

O pipeline-base — download yt-dlp, frames ffmpeg, backends Groq/OpenAI Whisper, o modo focado `--start`/`--end`, o hook de SessionStart e a instalação multi-superfície — vem do projeto original `claude-video` e funciona sem mudança (ver [Créditos](#créditos)).

---

O Claude lê uma página, roda um script, navega um repo. O que ele não faz, de fábrica, é *assistir um vídeo*. Você cola um link do YouTube e ele tem que adivinhar pelo título ou puxar um transcript que perde 90% do que está na tela.

Com o `/watch` você cola uma URL ou um caminho local, faz uma pergunta, e o Claude baixa o vídeo, extrai frames numa taxa auto-escalada, puxa um transcript com timestamp (captions grátis quando há, Whisper como fallback) e `Read` cada frame como imagem. Na hora de responder, ele *viu* o vídeo e *ouviu* o áudio.

```
/watch https://youtu.be/dQw4w9WgXcQ o que acontece aos 30 segundos?
```

## Por que isso existe

Construí isso porque vivo usando vídeo pra acompanhar conteúdo. Se vejo um vídeo do YouTube bombando, quero saber como o criador estruturou o gancho — o que está na tela nos 3 primeiros segundos, o que ele falou, por que funcionou. Isso significava assistir na mão com um bloco de notas. Agora eu só colo a URL e pergunto.

A outra metade é resumo. A maioria dos vídeos não merece 20 minutos da minha atenção. Eu passo a URL pro Claude, ele puxa o transcript e me diz o que de fato aconteceu. Se o visual importa, os frames vêm junto. Se é um podcast ou talking head, o transcript basta.

O Claude é ótimo em ler e sintetizar — mas até agora vídeo era o único input que eu não conseguia passar pra ele. Colar um link do YouTube não dava nada útil. O `/watch` fecha essa lacuna.

## Pra que as pessoas usam

**Analisar conteúdo de outra pessoa.** `/watch https://youtu.be/<video-viral> que gancho eles abriram?` O Claude olha os primeiros frames, lê o transcript de abertura, quebra a estrutura. O mesmo pra ad creative, lançamento de concorrente, intro de podcast — qualquer coisa onde o *como* importa tanto quanto o *quê*.

**Diagnosticar um bug por vídeo.** Te mandam um screen recording de algo quebrado. `/watch bug-repro.mov o que está dando errado?` O Claude assiste a gravação, acha o frame onde o problema aparece, descreve o que está na tela e muitas vezes pega a causa sem você nunca abrir o arquivo.

**Resumir um vídeo.** `/watch https://youtu.be/<coisa-longa> resume isso` faz o óbvio — puxa a estrutura, os momentos-chave, o que foi realmente dito e mostrado. Mais rápido que assistir em 2x.

## Como funciona

1. **Você cola um vídeo e uma pergunta.** URL (tudo que o yt-dlp suporta — YouTube, Loom, TikTok, X, Instagram, e mais umas centenas) ou um caminho local (`.mp4`, `.mov`, `.mkv`, `.webm`).
2. **O `yt-dlp` baixa.** Pra URLs, num diretório de trabalho temporário. Pra arquivos locais, sem download — só é sondado no lugar.
3. **O `ffmpeg` extrai frames numa taxa auto-escalada.** O orçamento de frames é consciente da duração: ≤30s pega ~30 frames, 30-60s pega ~40, 1-3min pega ~60, 3-10min pega ~80, mais longo pega 100 esparso. Tetos rígidos: 2 fps, 100 frames. JPEGs a 512px de largura por padrão — sobe com `--resolution 1024` se o Claude precisar ler texto na tela.
4. **O transcript vem de um de dois lugares.** Primeira tentativa: `yt-dlp` puxa captions nativos (manual ou auto-gerados) da fonte. Grátis, instantâneo, razoavelmente preciso. Fallback: extrai um clipe de áudio mono 16 kHz e manda pro Whisper — `whisper-large-v3` da Groq (preferido — mais barato e rápido) ou `whisper-1` da OpenAI.
5. **Frames + transcript são entregues ao Claude.** O script imprime os caminhos dos frames com marcadores `t=MM:SS` e o transcript com timestamps. O Claude `Read` cada frame em paralelo — JPEGs renderizam direto como imagem no contexto dele.
6. **O Claude responde fundamentado no que está de fato na tela e no áudio.** Não "com base na descrição" ou "segundo o título". Ele viu os frames. Ouviu o transcript. Responde como quem assistiu o vídeo.
7. **Limpeza.** O script imprime um diretório de trabalho no fim. Se você não vai fazer follow-up, o Claude remove.

## O objetivo final: o vídeo vira uma nota conectada

O `/watch` não para na resposta. O objetivo de verdade é transformar o vídeo numa **nota estruturada e conectada no seu "Second Brain" do Obsidian** — enquadrada pelo *porquê* você assistiu (o `--intent`). Ele grava em duas camadas:

**1. O artefato bruto — `report.md`** (Step 4.4), montado em `raw/watched/<slug>/` junto com as **hero frames** escolhidas. Esquema fixo: frontmatter (source, title, duration, watched_at, intent, hero_frames, transcript_source), **TL;DR** pela lente do seu intent, **momentos-chave**, o **microscópio do hook 0-10s** (frame-a-frame + transcript word-level + o padrão de gancho), **perfil editorial** (cortes/min, duração de shot, motion por shot, movimento de câmera, fingerprint de estilo), **citações**, **entidades** (pessoas / empresas / ferramentas como `[[wikilinks]]`), **conceitos** e o **transcript** completo.

**2. Ingestão no wiki** (Step 4.5, só com o seu consentimento). Se o vault tem um `CLAUDE.md` com uma Ingest op, ela roda contra o relatório e grava/atualiza:
- `wiki/entities/` — páginas das pessoas, empresas e ferramentas mencionadas
- `wiki/concepts/` — os frameworks e modelos mentais que apareceram
- `wiki/sources/` — a página do próprio vídeo com TL;DR + citações
- uma linha no `log.md`

Sem um `CLAUDE.md` no vault, ele cai num ingest genérico: a linha no `log.md` mais o relatório montado.

**O objetivo unificador:** o vídeo vira um nó de primeira classe no seu grafo de conhecimento — as pessoas, ferramentas e conceitos dele ligados via `[[wikilink]]` às notas que você já tem, enquadrados pelo seu motivo de assistir. Detalhe: o script *gera* o `report.md` sozinho, mas o wiki só é populado se o seu vault definir a Ingest op — a skill delega esse passo ao contrato do seu Second Brain, em vez de trazer um pronto.

## Ler o estilo cinematográfico (perfil editorial)

Um vídeo curto — de até ~2-3 minutos — é o ponto ideal pra "ler o estilo": o orçamento dá ~60-80 frames (um por corte), o transcript inteiro e o perfil editorial completo. O que sai é um **brief de estilo**, parte **medido**, parte **inferido**:

**Medido (números reais, sem opencv):**
- **Ritmo** — cortes/min + duração média/mediana de shot. É o fingerprint de pacing: "cortes secos, shot médio 1,8s" (estilo MTV/Fireship) vs "shots de 8s" (contemplativo).
- **Motion** — `signalstats` por shot: quais planos são agitados vs parados.
- **Câmera** — rótulo por shot (pan / tilt / zoom / estático / handheld) + o movimento dominante, via `vidstabdetect`.

**Inferido pelo Claude (lendo os frames):**
- Paleta / look de cor, enquadramento e composição (close vs wide, simetria), iluminação (high/low-key), uso de texto na tela, transições e lente aparente (grande-angular vs tele).
- Um **fingerprint de estilo de uma linha** (já é uma seção do `report.md`).

> **Densidade:** o motion e o classificador de câmera amostram o vídeo **inteiro** (4-8 fps), não só os frames que o Claude vê. Movimento *dentro* de um shot é capturado mesmo o Claude vendo um frame por plano.

**Limites honestos:**
- Grading/LUT, lente, profundidade de campo e temperatura de cor são **inferidos dos frames, não medidos**.
- O *sentido* do movimento (esquerda/direita) é heurístico — confiável só pro **eixo** (pan vs tilt vs zoom vs handheld vs estático).
- Áudio: só a fala (transcript). Não analisa trilha/música/mixagem.

Como rodar — o `--intent` molda o report pra esse eixo:
```
/watch seu-video.mp4 estilo cinematográfico e linguagem de câmera
```

O brief resultante (pacing + câmera + look + fingerprint) serve de direção pronta pra ferramentas de geração/motion de vídeo.

**Exemplo real:** [`examples/avatar-reel-cinematic-style.md`](examples/avatar-reel-cinematic-style.md) — diagnóstico de estilo de um reel do Avatar, saída de uma execução real do `/watch`.

## Orçamento de frames — por que importa

O custo de token é dominado pelos frames. Cada frame é uma imagem; tokens de imagem somam rápido. A lógica de auto-fps existe pra você não estourar o orçamento de contexto num scan esparso de um vídeo de 30 minutos que teria sido melhor respondido por uma janela focada de 30 segundos.

| Duração | Orçamento de frames padrão | O que você ganha |
|---------|----------------------------|------------------|
| ≤30 s | ~30 frames | Denso — basicamente todo momento-chave |
| 30 s - 1 min | ~40 frames | Ainda denso |
| 1 - 3 min | ~60 frames | Confortável |
| 3 - 10 min | ~80 frames | Esparso mas utilizável |
| > 10 min | 100 frames | Aviso de "scan esparso" — re-rode focado |

Quando o usuário nomeia um momento ("por volta de 2:30", "os últimos 30 segundos", "de 0:45 a 1:00"), passe `--start` / `--end`. O modo focado usa orçamentos por segundo mais densos, limitados a 2 fps. Bem mais útil que uma passada esparsa pelo vídeo inteiro.

## Instalar

| Superfície | Instalação |
|------------|------------|
| **Claude Code** | `/plugin marketplace add inematds/claude-watch` e depois `/plugin install watch@claude-watch` |
| **claude.ai** (web) | [Baixe o `watch.skill`](https://github.com/inematds/claude-watch/releases/latest) → Settings → Capabilities → Skills → `+` |
| **Codex** | `git clone https://github.com/inematds/claude-watch.git ~/.codex/skills/watch` |
| **Manual / dev** | `git clone https://github.com/inematds/claude-watch.git ~/.claude/skills/watch` |
| **Configuração** | Opcional: `export WATCH_VAULT_DIR=/caminho/do/seu/vault/obsidian` pra ligar o auto-save. Auto-detecta `~/Second brain/`, `~/Documents/Obsidian/`, `~/Obsidian/`. |

### Claude Code

```
/plugin marketplace add inematds/claude-watch
/plugin install watch@claude-watch
```

Atualize depois com `/plugin update watch@claude-watch`.

### claude.ai (web)

1. [Baixe o `watch.skill`](https://github.com/inematds/claude-watch/releases/latest) do último release.
2. Vá em Settings → Capabilities → Skills.
3. Clique `+` e solte o arquivo.

Ative "Code execution and file creation" em Capabilities antes — a skill chama `ffmpeg` e `yt-dlp`, então não roda sem isso.

### Codex

```bash
git clone https://github.com/inematds/claude-watch.git ~/.codex/skills/watch
```

### Manual (desenvolvedor)

```bash
git clone https://github.com/inematds/claude-watch.git ~/.claude/skills/watch
```

## Primeiro run

Na primeira chamada `/watch`, a skill roda `scripts/setup.py --check`. Se `ffmpeg` / `yt-dlp` não estiverem no PATH, ou nenhuma chave Whisper estiver setada, ela te guia pra resolver:

- **macOS** — auto-roda `brew install ffmpeg yt-dlp`.
- **Linux** — imprime os comandos exatos `apt` / `dnf` / `pipx`.
- **Windows** — imprime os comandos `winget` / `pip`.
- **Chave de API** — cria `~/.config/watch/.env` (modo `0600`) com placeholders comentados pra `GROQ_API_KEY` (preferido) e `OPENAI_API_KEY`.

Depois do setup, o preflight é silencioso e o `/watch` simplesmente funciona. O check é um lookup de sub-100ms, então não te atrasa nos runs seguintes.

## Use suas próprias chaves

Captions cobrem a maioria dos vídeos públicos de graça. O fallback Whisper só entra quando o vídeo genuinamente não tem trilha de legenda — tipicamente arquivos locais, TikToks, alguns Vimeos e o eventual upload de YouTube sem legenda.

| Capacidade | O que você precisa | Custo |
|------------|--------------------|-------|
| Download + captions nativos | `yt-dlp` + `ffmpeg` | Grátis |
| Fallback Whisper (preferido) | [Chave Groq](https://console.groq.com/keys) — `whisper-large-v3` | Barato, rápido |
| Fallback Whisper (alt) | [Chave OpenAI](https://platform.openai.com/api-keys) — `whisper-1` | Preço padrão |
| Desligar o Whisper de vez | `--no-whisper` | Grátis, só frames quando não há captions |

## Uso

```
/watch https://youtu.be/dQw4w9WgXcQ o que acontece aos 30 segundos?
/watch https://www.tiktok.com/@user/video/123 resume isso
/watch ~/Movies/screen-recording.mp4 quando a UI quebra?
/watch https://vimeo.com/123 que ferramentas ela menciona?
```

Focado numa seção específica — orçamento de frames mais denso, menos token:
```
/watch https://youtu.be/abc --start 2:15 --end 2:45
/watch video.mp4 --start 50 --end 60
/watch "$URL" --start 1:12:00            # de 1h12m até o fim
```

Outros botões (passados pro `scripts/watch.py`):

- `--max-frames N` — baixa o teto de frames pra um orçamento de token mais apertado.
- `--resolution W` — sobe a largura do frame pra 1024 px quando o Claude precisa ler texto na tela (slides, terminais, código).
- `--fps F` — sobrescreve o cálculo de auto-fps (ainda limitado a 2 fps).
- `--whisper groq|openai` — força um backend Whisper específico.
- `--no-whisper` — desliga a transcrição de vez; só frames.
- `--out-dir DIR` — guarda os arquivos de trabalho num lugar específico (padrão: tmp auto-gerado).

## Limites

- **Melhor acurácia: abaixo de 10 minutos.** Acima disso o script imprime um aviso de "scan esparso" — re-rode focado na parte que importa com `--start`/`--end`.
- **Tetos rígidos: 2 fps, 100 frames.** A contagem de frames dirige o custo de token; o script força isso mesmo quando a conta de auto-fps implicaria mais.
- **Limite de upload do Whisper: 25 MB.** A mono 16 kHz isso dá uns 50 minutos de áudio. Vídeos maiores precisam de captions ou de `--start`/`--end` pra uma janela menor.
- **Sem plataformas privadas.** A skill não loga em nada. Só URLs públicas e arquivos locais. Se o yt-dlp não alcança sem auth, o `/watch` também não.

## Estrutura

```
.
├── SKILL.md                 # contrato da skill — carregado pelas três superfícies
├── scripts/
│   ├── watch.py             # entry point — orquestra download → frames → transcript
│   ├── download.py          # wrapper do yt-dlp
│   ├── frames.py            # frames ffmpeg + auto-fps + motion (signalstats) + câmera (vidstabdetect)
│   ├── pacing.py            # métricas editoriais (cortes/min, shot length, motion, movimento de câmera)
│   ├── hook.py              # microscópio do hook 0-10s
│   ├── report.py            # emissor do report.md estruturado
│   ├── transcribe.py        # parse de VTT + dedupe + orquestração Whisper
│   ├── whisper.py           # clients Groq / OpenAI (pure stdlib)
│   ├── setup.py             # preflight + instalador
│   └── build-skill.sh       # monta dist/watch.skill pro upload no claude.ai
├── hooks/                   # hook de status no SessionStart (só Claude Code)
├── .claude-plugin/          # plugin.json + marketplace.json (Claude Code)
├── .codex-plugin/           # empacotamento codex
└── .github/workflows/       # release.yml — auto-monta watch.skill no push de tag
```

## Desenvolver

```bash
# Monta o bundle de upload do claude.ai:
bash scripts/build-skill.sh      # → dist/watch.skill

# Roda os testes (stdlib unittest, sem dependência de pytest):
python3 -m pytest scripts/tests/ -q   # ou: python3 -m unittest discover scripts/tests
```

Releasing: tag `vX.Y.Z`, push da tag. O workflow monta `dist/watch.skill` e anexa ao release do GitHub.

Veja o [CHANGELOG.md](CHANGELOG.md) pro histórico de versões.

## Créditos

O `/watch` é construído sobre o **[claude-video](https://github.com/bradautomates/claude-video)** do **[Bradley Bonanno](https://github.com/bradautomates)**. A skill `/watch` original — o download yt-dlp, o pipeline ffmpeg, os backends Groq/OpenAI Whisper, o fluxo de instalação e o hook de SessionStart — é trabalho dele, lançado sob a licença MIT. Este repo estende com extração de frames por corte de cena, o microscópio do hook 0-10s, o motion por shot via signalstats, o `report.md` estruturado e o auto-save no Obsidian.

Autor original e detentor do copyright: **Bradley Bonanno** (ver [LICENSE](LICENSE)). Contribuidores estão listados em [AUTHORS.md](AUTHORS.md).

## Open source

Licença MIT.

Construído sobre `yt-dlp`, `ffmpeg` e a `Read` multimodal do Claude. Transcrição Whisper via [Groq](https://groq.com) ou [OpenAI](https://openai.com).

---

[github.com/inematds/claude-watch](https://github.com/inematds/claude-watch) · [Créditos](#créditos) · [LICENSE](LICENSE)
