#!/usr/bin/env bash
# Собирает Wendigo.apk: игра (../index.html, ../js, ../three.min.js) + Java-код сети.
# Нужны: Java 11+, Python 3 с Pillow, npm, curl. Android SDK не нужен.
set -euo pipefail
cd "$(dirname "$0")"
TOOLS=.tools; mkdir -p "$TOOLS" build
fetch() { for i in 1 2 3 4 5 6; do curl -sSfL -o "$2" "$1" && return 0; sleep $((2 ** i)); done; return 1; }
M=https://repo.maven.apache.org/maven2
[ -f "$TOOLS/android.jar" ] || fetch $M/com/google/android/android/4.1.1.4/android-4.1.1.4.jar "$TOOLS/android.jar"
[ -f "$TOOLS/dx.jar" ] || fetch $M/com/jakewharton/android/repackaged/dalvik-dx/11.0.0_r3/dalvik-dx-11.0.0_r3.jar "$TOOLS/dx.jar"
[ -f "$TOOLS/apksig.jar" ] || fetch $M/com/android/tools/build/apksig/2.3.0/apksig-2.3.0.jar "$TOOLS/apksig.jar"
if [ ! -f "$TOOLS/apktool.jar" ]; then
  (cd "$TOOLS" && npm pack apktool-jar@2.4.1 -q >/dev/null && tar xzf apktool-jar-2.4.1.tgz \
    && mv package/bin/apktool_2.4.1.jar apktool.jar && rm -rf package apktool-jar-2.4.1.tgz)
fi
KS=keystore.p12; PASS=${APK_KEY_PASS:-wendigo}
[ -f "$KS" ] || keytool -genkeypair -keystore "$KS" -storetype PKCS12 -storepass "$PASS" -keypass "$PASS" \
  -alias wendigo -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Wendigo" >/dev/null 2>&1

# 1) Java → dex
rm -rf build/stubs build/classes && mkdir -p build/stubs build/classes
javac -nowarn --release 8 -encoding UTF-8 -d build/stubs stubs/android/webkit/JavascriptInterface.java
javac -nowarn --release 8 -encoding UTF-8 -cp "$TOOLS/android.jar:build/stubs" -d build/classes $(find java -name '*.java')
java -cp "$TOOLS/dx.jar" com.android.dx.command.Main --dex --min-sdk-version=24 --output=build/classes.dex build/classes
# 2) ресурсы и игра
rm -rf app/assets && mkdir -p app/assets/js
cp ../index.html ../three.min.js app/assets/ && cp ../js/*.js app/assets/js/
python3 make_icon.py app/res
java -jar "$TOOLS/apktool.jar" b app -o build/unsigned.apk -p "$TOOLS/framework"
# 3) добавляем classes.dex и подписываем
python3 - <<'PY'
import zipfile, shutil
src, dst = 'build/unsigned.apk', 'build/withdex.apk'
with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, 'w') as zo:
    for it in zi.infolist():
        if it.filename == 'classes.dex': continue
        zo.writestr(it, zi.read(it.filename), compress_type=it.compress_type)
    zo.write('build/classes.dex', 'classes.dex', compress_type=zipfile.ZIP_DEFLATED)
PY
java --add-exports java.base/sun.security.x509=ALL-UNNAMED -cp "$TOOLS/apksig.jar" Sign.java "$KS" "$PASS" wendigo build/withdex.apk ../Wendigo.apk
echo "Готово: wendigo-game/Wendigo.apk"
