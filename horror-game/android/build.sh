#!/usr/bin/env bash
# Собирает Android-приложение «Он рядом» (APK) из ../index.html и ../three.min.js.
# Нужны: Java 11+, Python 3 с Pillow, npm, curl. Android SDK не нужен.
set -euo pipefail
cd "$(dirname "$0")"
TOOLS=.tools
mkdir -p "$TOOLS" build

# apktool (включает aapt и smali) и apksig (подпись v2)
if [ ! -f "$TOOLS/apktool.jar" ]; then
  (cd "$TOOLS" && npm pack apktool-jar@2.4.1 -q >/dev/null && tar xzf apktool-jar-2.4.1.tgz \
    && mv package/bin/apktool_2.4.1.jar apktool.jar && rm -rf package apktool-jar-2.4.1.tgz)
fi
if [ ! -f "$TOOLS/apksig.jar" ]; then
  for i in 1 2 3 4 5; do  # Maven Central иногда отвечает 429 — повторяем
    curl -sSfL -o "$TOOLS/apksig.jar" \
      https://repo.maven.apache.org/maven2/com/android/tools/build/apksig/2.3.0/apksig-2.3.0.jar && break
    sleep $((2 ** i))
  done
fi

# ключ подписи (создаётся один раз; сохраните его, чтобы ставить обновления поверх)
KS=keystore.p12; PASS=${APK_KEY_PASS:-onryadom}
if [ ! -f "$KS" ]; then
  keytool -genkeypair -keystore "$KS" -storetype PKCS12 -storepass "$PASS" -keypass "$PASS" \
    -alias onryadom -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=On Ryadom" >/dev/null 2>&1
fi

cp ../index.html ../three.min.js app/assets/
python3 make_icon.py app/res
java -jar "$TOOLS/apktool.jar" b app -o build/unsigned.apk -p "$TOOLS/framework"
# старый apksig заглядывает во внутренний класс JDK
java --add-exports java.base/sun.security.x509=ALL-UNNAMED -cp "$TOOLS/apksig.jar" Sign.java "$KS" "$PASS" onryadom build/unsigned.apk ../OnRyadom.apk
echo "Готово: horror-game/OnRyadom.apk"
