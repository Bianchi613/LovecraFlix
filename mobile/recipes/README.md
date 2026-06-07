# Receitas locais do python-for-android (`p4a.local_recipes`)

Esta pasta contém receitas que **substituem** as oficiais do
python-for-android durante o build do APK (`buildozer.spec` aponta
`p4a.local_recipes = %(source.dir)s/recipes`). Existem porque o player de
vídeo (`ffpyplayer` — o coração do app) é incompatível com o toolchain
"de ponta" que o p4a usa por padrão hoje.

## O problema original

`ffpyplayer` v4.5.1 tem bindings Cython **compilados** que referenciam APIs
do FFmpeg que já não existem na versão atual usada pelo p4a (FFmpeg 8.0.1):
`libavcodec/avfft.h`, `av_get_channel_layout_nb_channels`,
`AVFrame.key_frame`, etc. Resultado: o build quebrava com erros de
"header not found" / símbolos inexistentes.

## A estratégia escolhida: travar no combo histórico compatível

Em vez de trocar de player de vídeo (rejeitado — vídeo é o coração do app),
travamos as peças do toolchain na combinação exata em que o p4a oficial
fixou o `ffpyplayer` em `v4.5.1`: o commit `af04bee3` (2024-06-02,
"ffpyplayer: update to 4.5.1"). Nesse momento, o p4a usava:
`python3 = 3.11.5`, `hostpython3 = 3.11.5`, `ffmpeg = n4.3.1`.

| Receita | Versão travada | Origem |
|---|---|---|
| [`ffmpeg/`](ffmpeg/__init__.py) | `n4.3.1` | cópia verbatim do commit `af04bee3` |
| [`python3/`](python3/__init__.py) | `3.11.5` | cópia verbatim do commit `af04bee3`, com pequenos ajustes (ver abaixo) |
| [`hostpython3/`](hostpython3/__init__.py) | `3.11.5` | reescrita a partir da receita **atual** do p4a (ver "Por que reescrita, não cópia") |
| [`ffpyplayer/`](ffpyplayer/__init__.py) | `v4.5.1` | receita atual + patch que remove bindings mortos do `avfft.h` |

## Por que isso gerou uma cascata de pequenos bugs

O **motor** que orquestra o build (`pythonforandroid/recipe.py`) **não está
travado** — é a versão atual (2026), que evoluiu desde 2024. Então temos um
"híbrido": peças antigas (nossas receitas) rodando dentro de um motor novo.
Cada incompatibilidade é o motor novo chamando algo que a peça antiga não
tem (ou chamando do jeito antigo algo que a peça nova mudou de formato).

Cada uma dessas foi diagnosticada **lendo o traceback exato** e comparando
com o código-fonte real do p4a (clone local + `git show <commit>:<path>`)
— nunca por tentativa e erro às cegas. Veja os comentários no topo de cada
arquivo de receita para o detalhe de cada ajuste; resumo cronológico:

1. **`python3` ≠ `hostpython3`**: o p4a exige que as duas tenham
   exatamente a mesma versão. Sem a receita local de `hostpython3`, ela
   ficava na versão padrão (3.14.2) enquanto `python3` estava em 3.11.5.
   → Criada a receita local de `hostpython3` travada em 3.11.5.

2. **`Sqlite3Recipe.get_lib_dir` não existe mais**: o código de 2024 do
   `python3` chamava `recipe.get_lib_dir(arch)` na receita de `sqlite3`
   (não travada — usa a versão atual). A receita atual de `sqlite3` foi
   refatorada de `NDKRecipe` (que tinha `get_lib_dir`) para `Recipe` simples
   (só tem `get_build_dir`, com `built_libraries = {'libsqlite3.so': '.'}`).
   → `python3/__init__.py`: trocado `get_lib_dir(arch)` por
   `get_build_dir(arch.arch)`.

3. **`'str' object has no attribute 'stdout'`**: o código de 2024 chamava
   `sh.Command(...)('config.guess')().stdout.strip().decode('utf-8')` —
   API de uma versão antiga da lib `sh` que devolvia um objeto com
   `.stdout` em bytes. A versão atual da `sh` já devolve string pronta.
   → `python3/__init__.py`: simplificado para só `.strip()` — confirmado
   comparando com a receita `python3` atual, que faz exatamente isso.

4. **`'HostPython3Recipe' object has no attribute 'pip'`**: o maior dos
   ajustes. A receita `hostpython3` de 2024 só compilava o Python "cru" e
   copiava o binário — não instalava `pip`. O motor **atual**
   (`recipe.py`, não travado) foi reescrito e agora exige que a receita do
   hostpython exponha uma API inteira de pip/site-packages
   (`.pip`, `.local_bin`, `.site_dir`, `.site_root`...) que a receita
   antiga nunca teve.
   → **Por que reescrita, e não remendo**: tentar reimplementar essa API à
   mão na receita antiga seria reinventar (mal) algo que o p4a atual já
   resolve direito. Em vez disso, `hostpython3/__init__.py` é uma cópia da
   receita **hostpython3 atual** (já 100% compatível com o motor de hoje —
   `configure --prefix` + `make install` + `ensurepip` + `fix_pip_shebangs`),
   só com `version`/`url` redirecionados para 3.11.5 e sem o
   `fix_ensurepip.patch` (específico de um bug do Python 3.14, nunca
   existiu para 3.11.5).

5. **`configure: error: invalid or missing build python binary
   .../native-build/python3`**: efeito colateral do item 4 — o código do
   `python3` montava o caminho do binário do hostpython "na mão"
   (`get_path_to_python() + "python3"`), formato que batia com o layout da
   receita antiga (binário solto em `native-build/`). A receita nova de
   `hostpython3` usa outro layout (`root/usr/local/bin/python`).
   → `python3/__init__.py`: trocado o caminho hardcoded pela propriedade
   `python_exe` da receita do hostpython — que cada uma expõe corretamente
   para o seu próprio layout, e é exatamente o que a receita `python3`
   atual faz para essa mesma chamada.

## Resultado

Build #13 (commit `5d5cc18`, 2026-06-07) — **sucesso em 12m52s**, artifact
`lovecraflix-apk` gerado com `ffpyplayer` funcionando. Ver duração das
tentativas anteriores para sentir a curva de progresso real (cada falha
foi mais longe que a anterior — não é "estagnado", é "fechando costuras"):
1m32s → 5m19s → 5m21s → 11m12s → **sucesso**.

## Se algo quebrar de novo (ex: ao atualizar alguma versão)

O padrão se repete: leia o traceback exato, clone o p4a
(`git clone https://github.com/kivy/python-for-android /tmp/p4a_check`),
compare a receita travada (aqui) com a atual (`git show <commit>:<path>`
ou o arquivo em `pythonforandroid/recipes/.../__init__.py` no clone), e
aplique o mesmo ajuste que a receita atual já faz. Não é preciso adivinhar
— a resposta certa quase sempre já existe no código atual do p4a.
