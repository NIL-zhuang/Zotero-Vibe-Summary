#!/usr/bin/env bash
# 把 plugin/src/ 下的源码打包成 paper-bridge.xpi
# 用法：bash plugin/build.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$DIR/src"
OUT="$DIR/paper-bridge.xpi"

cd "$SRC"
rm -f "$OUT"
zip -q -r "$OUT" manifest.json bootstrap.js
echo "已生成: $OUT"
unzip -l "$OUT"
