# Fluxo Git

Este projeto usa um fluxo simples baseado em `main` protegida e branches curtas.

- `main`: versão estável/deployável.
- `feature/<nome>`: funcionalidade.
- `fix/<nome>`: correção.
- `docs/<nome>`: documentação.
- `chore/<nome>`: manutenção.

Toda mudança deve preferencialmente entrar em `main` por Pull/Merge Request após CI.
Tags seguem SemVer (`v0.3.0`, `v0.3.1`, `v0.4.0`).

Nunca versione `.env`, PATs, OAuth secrets, chaves privadas, dumps, volumes ou ZIPs de backup.
