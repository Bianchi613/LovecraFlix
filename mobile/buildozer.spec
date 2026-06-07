[app]

title = LovecraFlix
package.name = lovecraflix
package.domain = org.lovecraflix

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json
source.exclude_dirs = .emoji_cache,__pycache__,.buildozer,bin,screens/__pycache__

version = 0.1

requirements = python3,kivy==2.3.1,kivymd==1.2.0,requests,pillow,ffpyplayer

# Receita customizada do ffpyplayer (em mobile/recipes/) — corrige um bug de
# compatibilidade entre as receitas oficiais ffpyplayer/ffmpeg do toolchain
# (ver comentário em recipes/ffpyplayer/__init__.py para detalhes).
p4a.local_recipes = %(source.dir)s/recipes

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icone/icon.png
presplash.filename = %(source.dir)s/icone/LovecraFlix.png

# Permissão de rede — o app conversa com o backend FastAPI via HTTP na LAN
android.permissions = INTERNET

# Apps com targetSdk >= 28 bloqueiam tráfego HTTP puro por padrão; o backend
# do LovecraFlix roda em http:// na rede local (sem HTTPS), então liberamos
# cleartext globalmente para o app conseguir falar com ele.
# OBS: essa opção espera um CAMINHO DE ARQUIVO (o Buildozer faz open() nela),
# não o texto direto — por isso aponta pro extra_manifest_args.txt.
android.extra_manifest_application_arguments = %(source.dir)s/extra_manifest_args.txt

android.api = 33
android.minapi = 24
android.archs = arm64-v8a

android.allow_backup = True

# Aceita as licenças do Android SDK automaticamente — sem isso o sdkmanager
# fica esperando uma resposta "y" interativa, que nunca chega no CI e quebra
# a instalação do build-tools (erro "Aidl not found").
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1
