#!/usr/bin/env bash
# Zaklada repozytorium git z tej zawartosci i wypycha je na zdalny serwer.
#
#   ./push.sh git@github.com:UZYTKOWNIK/przechyl.git
#   ./push.sh https://github.com/UZYTKOWNIK/przechyl.git
#
# Repozytorium po stronie serwera musi juz istniec i byc puste.
# Z zainstalowanym gh mozesz je zalozyc od razu:
#   gh repo create przechyl --public --source=. --remote=origin --push

set -euo pipefail

REMOTE="${1:-}"
if [ -z "$REMOTE" ]; then
  echo "uzycie: $0 <adres-zdalnego-repo>" >&2
  echo "np.   : $0 git@github.com:mt3o/przechyl.git" >&2
  exit 1
fi

cd "$(dirname "$0")"

if [ ! -d .git ]; then
  git init -b main
  echo "zainicjowano repozytorium"
fi

git add -A
if git diff --cached --quiet; then
  echo "brak zmian do zatwierdzenia"
else
  git commit -m "Przechyl — generator dzwiekow bilateralnych"
  echo "zatwierdzono"
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE"
else
  git remote add origin "$REMOTE"
fi

git push -u origin main
echo
echo "gotowe. Zeby opublikowac strone przez GitHub Pages:"
echo "  Settings -> Pages -> Source: Deploy from a branch -> main / (root)"
