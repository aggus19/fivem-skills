# FiveM Skills — `fivem-development`

Skill para agentes de IA (Claude Code, OpenAI Codex, Cursor y otras herramientas compatibles con Agent Skills) que trae conocimiento **actualizado al 7 de octubre de 2026** sobre desarrollo en FiveM, scripts verificadores y plantillas listas para producción.

> Las versiones se verificaron contra fuentes primarias (GitHub releases, npm, docs.fivem.net, forum.cfx.re, API de artifacts) el **2026-10-07**. Ver [`skills/fivem-development/references/versions.md`](skills/fivem-development/references/versions.md).

## Qué incluye

| Área | Contenido |
|---|---|
| **SKILL.md** | Reglas no negociables (autoridad del servidor, no inventar natives, detectar el stack, APIs actuales, presupuesto de rendimiento, licencias), tabla de ruteo a referencias y flujos de trabajo (crear, modificar, auditar, convertir, optimizar). |
| **49 referencias (~12.300 líneas)** | **Plataforma:** versiones y línea de tiempo de cambios · server.cfg/instalación/ACE · todas las convars y comandos con valores recomendados · txAdmin completo · OneSync/entidades/state bags/routing buckets · GTA V Enhanced. **Scripting:** fxmanifest (todas las directivas) · runtimes CfxLua 5.4.8/JS/TS/C# · todos los eventos nativos · guía de natives + 699 natives esenciales verificadas · NUI/DUI · tooling · debugging. **ox:** ox_lib completo en 6 archivos (UI, core, world, utilidades, JS) · oxmysql · optimización de bases de datos (MariaDB/MySQL, índices, my.cnf, backups) · ox_inventory · ox_target · ox_core · ox_doorlock/ox_fuel. **Frameworks:** Qbox + ecosistema qbx · ESX Legacy 1.15.2 + ecosistema · QBCore (refactor 2026) · ND/vRP · bridge multi-framework · recursos de la comunidad por categoría. **Gameplay:** patrones · diseño de sistemas RP · vehículos y handling · mapeo/streaming/ropa. **Calidad:** qué usar vs qué evitar · seguridad · anticheat · checklist de auditoría · rendimiento + cookbook + escalado de servidores grandes · licencias (PLA 2026‑09‑10). |
| **Catálogo de natives** | `assets/natives/`: las **7.379** natives (6.436 GTA + 943 CFX) en 47 archivos por namespace, con firma Lua, lado, hash, build mínimo, nombres viejos y link a docs. Regenerable con `build_natives_catalog.py`. |
| **7 scripts** (Python, sin dependencias): `rcon.py` y `server_info.py` para probar recursos contra un servidor; ver más abajo. Los otros 5: | `natives.py` (busca/verifica natives, incluye nombres viejos, detecta natives inventadas y del lado equivocado) · `build_natives_catalog.py` (regenera el catálogo) · `manifest.py` (valida fxmanifest) · `audit.py` (backdoors conocidos, SQLi, confianza en el cliente, XSS en NUI, webhooks expuestos, `.cfg` inseguros, loops sin Wait, APIs obsoletas) · `scaffold.py` (genera recursos). |
| **Plantillas** | Recurso Lua con *bridge* que autodetecta Qbox / ESX / QBCore / standalone + ejemplo de tienda segura (las 5 validaciones del servidor) · NUI React 19 + Vite 8 + TypeScript 7 con target `chrome103` (CEF de FiveM Legacy). |
| **Configs** | `.luarc.json` (LuaLS + addon FiveM), `selene.toml` + std `cfx.yml`, `.stylua.toml`, `server.cfg.example`, workflow de GitHub Actions. |
| **Plugin de Claude Code** | Comandos `/fivem-new`, `/fivem-audit`, `/fivem-native` y el subagente `fivem-auditor`. |
| **Tests** | `python -m unittest discover -s tests -v` (offline, 35 tests). |

## Datos clave del baseline (2026-10-07)

- FXServer Legacy **Recommended 35245** / Latest 37150; después del **15-10-2026** los clientes no pueden entrar a servidores con builds viejas.
- Game build **3889** (`mp2026_01`, The Kortz Center Heist).
- **Lua 5.3 eliminado** (jun-2025): `lua54 'yes'` ya es opcional. **Node 16 eliminado**: Node 22 (Legacy).
- **OneSync forzado**; flags `sv_experimental*` eliminados.
- **GTA V Enhanced** en early access desde el 21-07-2026 con su propio servidor (*Cfx Server*, build 161); sin Asset Escrow todavía.
- **CommunityOx archivado** (abr-2026): ox_lib / oxmysql / ox_inventory / ox_target volvieron a `overextended/*` (ox_lib 3.40.0, oxmysql 2.14.3, ox_inventory 2.48.0, ox_target 1.18.1).
- Qbox **1.24.0** · ESX Legacy **1.15.2** (nuevo `esx_lib`) · QBCore se mudó a `github.com/qbcore-fivem/qb-core`.
- txAdmin **8.1.1** · CEF **M103** con JIT de V8 desactivado · PLA vigente del **10-09-2026** (Tebex es el único medio de cobro permitido).
- ox_inventory **≥ 2.47.6** (fixes de duplicación) y **sin soporte QBCore** desde 2.42 · QBCore tuvo un **refactor en mayo 2026** (`OnPlayerUpdated`, sin `QBConfig`/`QBShared`).
- C# `mono_rt2` expiró (30-06-2026) · `node_version` se ignora (todo Node 22) · Tailwind v4 no anda en CEF 103.
- Bases de datos: MariaDB 11.8/12.3 LTS o MySQL 8.4/9.7 LTS (MariaDB 10.6 y MySQL 8.0 ya son EOL).

## Instalación

### Claude Code: como plugin (recomendado)
```bash
# desde un repo de GitHub que contenga esta carpeta
/plugin marketplace add <usuario>/<repo>
/plugin install fivem-development@fivem-skills

# o localmente
/plugin marketplace add "C:/Users/Administrator/Documents/FiveM Skills"
/plugin install fivem-development@fivem-skills
```

### Claude Code: solo la skill
Copiá `skills/fivem-development/` a `~/.claude/skills/fivem-development/` (global) o a `.claude/skills/fivem-development/` dentro de tu proyecto.

### OpenAI Codex
Copiá `skills/fivem-development/` a `~/.agents/skills/` o a `.agents/skills/` del repo. `AGENTS.md` en la raíz da instrucciones de proyecto.

### Cursor
Cursor lee `.cursor/skills/`, `.agents/skills/` y también `.claude/skills/`: copiá la carpeta de la skill a cualquiera de esas rutas.

### Cualquier agente compatible (`npx skills`)
```bash
npx skills add <usuario>/<repo> --skill fivem-development
```

## Uso de los scripts
```bash
cd skills/fivem-development
python scripts/natives.py update                       # descarga la base oficial de natives (~3 MB, cache en ~/.cache/fivem-skill)
python scripts/natives.py show GetEntityCoords          # firma exacta cliente y servidor
python scripts/natives.py check ../../mi_recurso --strict
python scripts/manifest.py ../../mi_recurso
python scripts/audit.py ../../resources --min medium
python scripts/scaffold.py mi_tienda --out ../../resources/[custom] --nui
```

## Estructura
```
FiveM Skills/
├── .claude-plugin/        plugin.json + marketplace.json
├── skills/fivem-development/
│   ├── SKILL.md
│   ├── references/        49 documentos
│   ├── scripts/           natives.py · build_natives_catalog.py · manifest.py · audit.py · scaffold.py
│   └── assets/
│       ├── natives/       catálogo completo (47 archivos por namespace)
│       ├── templates/     resource-lua/ · nui-react-vite/
│       └── configs/       .luarc.json · selene.toml · cfx.yml · .stylua.toml · server.cfg.example · github-workflow.yml
├── commands/              /fivem-new · /fivem-audit · /fivem-native
├── agents/                fivem-auditor
├── docs/community-analysis/  evidencia: análisis y verificación de ~40 repos públicos de skills/MCP de FiveM
├── evals/                 casos de evaluación de la skill
├── tests/                 tests offline de los scripts
├── AGENTS.md · CHANGELOG.md · LICENSE
```

## Mantenimiento
Las versiones envejecen. Para actualizar el baseline: seguí la sección "How to re-verify" de `references/versions.md`, actualizá las tablas y `metadata.baseline-date` en `SKILL.md`, corré los tests y anotá los cambios en `CHANGELOG.md`.

## Fuentes principales
- Cfx.re docs: https://docs.fivem.net/docs/ · natives: https://docs.fivem.net/natives/ · descargas: https://docs.fivem.net/docs/server-download/
- Foro Cfx.re (anuncios 2026): https://forum.cfx.re/t/5422124 (build 35245) · https://forum.cfx.re/t/5412858 (Enhanced early access) · https://forum.cfx.re/t/5415045 (Dev Update #3)
- overextended: https://overextended.dev/docs · https://github.com/overextended
- Qbox: https://docs.qbox.re · ESX: https://docs.esx-framework.org/en · QBCore: https://qbcore.org/docs
- txAdmin: https://github.com/citizenfx/txAdmin/releases · PLA: https://fivem.net/terms
- Agent Skills: https://agentskills.io/specification · Claude Code plugins: https://code.claude.com/docs/en/plugins-reference

## Licencia
MIT. FiveM, Cfx.re y GTA V son marcas de sus respectivos dueños; este proyecto no está afiliado a Rockstar Games ni a Cfx.re.
