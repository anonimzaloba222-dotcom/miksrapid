#!/usr/bin/env bash
# Собирает duo-offline.html: Three.js встраивается прямо в файл (работает без интернета и без сервера).
# Требуется Node.js. Запуск: bash build-offline.sh
set -euo pipefail
cd "$(dirname "$0")"
TMP=$(mktemp -d)
python3 - "$TMP" <<'PY'
import sys
s = open('index.html', encoding='utf-8').read()
a = s.index('<script type="module">'); b = s.index('</script>', a)
open(sys.argv[1] + '/main.js', 'w', encoding='utf-8').write(s[a + len('<script type="module">'):b])
PY
(cd "$TMP" && npm init -y >/dev/null && npm i -s three@0.160.0 esbuild@0.24.0 >/dev/null \
  && ./node_modules/.bin/esbuild main.js --bundle --minify --format=iife --target=es2019 --legal-comments=none --outfile=out.js)
python3 - "$TMP" <<'PY'
import sys, re
s = open('index.html', encoding='utf-8').read()
js = open(sys.argv[1] + '/out.js', encoding='utf-8').read().replace('</script', '<\\/script')
s = re.sub(r'<!-- Карта импортов.*?</script>\s*', '', s, flags=re.S)
a = s.index('<script type="module">'); b = s.index('</script>', a) + len('</script>')
s = s[:a] + '<!-- Three.js r160 и код сцены встроены (офлайн-сборка) -->\n<script>\n' + js + '\n</script>' + s[b:]
s = s.replace('Подключение Three.js…', 'Запуск 3D…')
s = s.replace("Не удалось загрузить Three.js с CDN. Проверьте подключение к интернету.", "Не удалось запустить 3D. Проверьте, что браузер поддерживает WebGL.")
s = s.replace("Откройте страницу через локальный сервер с доступом к интернету.", "Попробуйте открыть файл в Chrome, Safari или Firefox.")
open('duo-offline.html', 'w', encoding='utf-8').write(s)
PY
rm -rf "$TMP"
echo "Готово: duo-offline.html"
