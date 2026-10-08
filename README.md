# FiveM Skills — `fivem-development`

Skill para agentes de IA (Claude Code, OpenAI Codex, Cursor y otras herramientas compatibles con Agent Skills) que trae conocimiento **actualizado al 7 de octubre de 2026** sobre desarrollo en FiveM, scripts de comprobación y plantillas de integración con límites de validación explícitos.

> Las versiones se verificaron contra fuentes primarias (GitHub releases, npm, docs.fivem.net, forum.cfx.re, API de artifacts) el **2026-10-07**. Ver [`skills/fivem-development/references/versions.md`](skills/fivem-development/references/versions.md).

## Qué incluye

| Área | Contenido |
|---|---|
| **SKILL.md** | Reglas no negociables (autoridad del servidor, no inventar natives, detectar el stack, APIs actuales, presupuesto de rendimiento, licencias), tabla de ruteo a referencias y flujos de trabajo (crear, modificar, auditar, convertir, optimizar). |
| **53 referencias** | **Plataforma:** versiones y línea de tiempo de cambios · server.cfg/instalación/ACE · todas las convars y comandos con valores recomendados · txAdmin completo · OneSync/entidades/state bags/routing buckets · GTA V Enhanced. **Scripting:** fxmanifest (todas las directivas) · runtimes CfxLua 5.4.8/JS/TS/C# · todos los eventos nativos · guía de natives + 699 natives esenciales verificadas · NUI/DUI · tooling · debugging. **ox:** ox_lib completo en 6 archivos (UI, core, world, utilidades, JS) · oxmysql · optimización de bases de datos (MariaDB/MySQL, índices, my.cnf, backups) · ox_inventory · ox_target · ox_core · ox_doorlock/ox_fuel. **Frameworks:** Qbox + ecosistema qbx · ESX Legacy 1.15.2 + ecosistema · QBCore (refactor 2026) · ND/vRP · bridge multi-framework · recursos de la comunidad por categoría. **Gameplay:** patrones · diseño de sistemas RP · vehículos y handling · mapeo/streaming/ropa. **Calidad:** qué usar vs qué evitar · seguridad · anticheat · checklist de auditoría · rendimiento + cookbook + escalado de servidores grandes · licencias (PLA 2026‑09‑10). |
| **Catálogo de natives** | `assets/natives/`: las **7.379** natives (6.436 GTA + 943 CFX) en 47 archivos por namespace, con firma Lua, lado, hash, build mínimo, nombres viejos y link a docs. Regenerable con `build_natives_catalog.py`. |
| **7 comandos + helper compartido** (Python 3.8+, sin dependencias): `rcon.py` y `server_info.py` para probar recursos contra un servidor; ver más abajo. Los otros 5: | `natives.py` (busca/verifica natives, incluye nombres viejos, detecta natives inventadas y del lado equivocado) · `build_natives_catalog.py` (regenera el catálogo) · `manifest.py` (valida fxmanifest) · `audit.py` (backdoors conocidos, SQLi, confianza en el cliente, XSS en NUI, webhooks expuestos, `.cfg` inseguros, loops sin Wait, APIs obsoletas) · `scaffold.py` (genera recursos). |
| **Plantillas** | Lua mínimo sin dependencias por defecto; perfil opcional `ox-shop` con *bridge* que autodetecta Qbox / ESX / QBCore / standalone + ejemplo de tienda con compensaciones comprobadas (compras desactivadas hasta integrar recuperación persistente) · NUI React 19 + Vite 8 + TypeScript 7 con target `chrome103` (CEF de FiveM Legacy). |
| **Configs** | `.luarc.json` (LuaLS + addon FiveM), `selene.toml` + std `cfx.yml`, `.stylua.toml`, `server.cfg.example`, workflow de GitHub Actions. |
| **Plugin de Claude Code** | Comandos `/fivem-new`, `/fivem-audit`, `/fivem-native` y el subagente `fivem-auditor`. |
| **Tests** | `python -m unittest discover -s tests -v` (offline); pruebas opcionales de lógica Lua 5.4 y compilación NUI real. Ver Validación. |

## Alcance general y plan

La skill se adapta a cada solicitud y al stack instalado: standalone, frameworks y
forks, Lua/JS/C#, interfaces existentes y datos con distintos propietarios. El perfil
mínimo no instala ox_lib, oxmysql ni una tienda. Los ejemplos de economía son opcionales
y requieren verificar contratos, persistencia y recuperación antes de habilitarlos.

- [Adaptación al proyecto](skills/fivem-development/references/project-adaptation.md).
- [Seguridad de triggers, callbacks, exports y operaciones](skills/fivem-development/references/security-validation.md), con pruebas negativas y de concurrencia/recuperación.
- [Diagnóstico de hitches](skills/fivem-development/references/hitch-diagnostics.md), separando scripts, sincronización, red, DB y host.
- [Plan de etapas y evidencia pendiente](docs/roadmap.md).

Las recomendaciones de DB y soporte se revisaron el **2026-10-08**. Una versión nueva
no garantiza mayor rendimiento ni ausencia de hitches; se exige compatibilidad y
medición. Las pruebas locales no equivalen a integración FXServer ni a un benchmark.

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
Copiá la carpeta completa a `~/.agents/skills/fivem-development/` o a `.agents/skills/fivem-development/` dentro del proyecto. Conservá `scripts/`, `references/` y `assets/`. Integrá la indicación de cargar esa `SKILL.md` en el `AGENTS.md` existente, sin reemplazar las instrucciones del servidor. Los helpers se resuelven desde la ubicación instalada de la skill. La skill no es un recurso de FXServer y no lleva `ensure` en `server.cfg`.

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
python scripts/scaffold.py mi_recurso --out "../../resources/[custom]"
python scripts/scaffold.py mi_tienda --profile ox-shop --out "../../resources/[custom]" --nui
```

## Estructura
```
FiveM Skills/
├── .claude-plugin/        plugin.json + marketplace.json
├── skills/fivem-development/
│   ├── SKILL.md
│   ├── references/        53 documentos
│   ├── scripts/           natives.py · build_natives_catalog.py · manifest.py · audit.py · scaffold.py
│   └── assets/
│       ├── natives/       catálogo completo (47 archivos por namespace)
│       ├── templates/     resource-minimal/ · resource-lua/ · nui-react-vite/
│       └── configs/       .luarc.json · selene.toml · cfx.yml · .stylua.toml · server.cfg.example · github-workflow.yml
├── commands/              /fivem-new · /fivem-audit · /fivem-native
├── agents/                fivem-auditor
├── docs/community-analysis/  evidencia: análisis y verificación de ~40 repos públicos de skills/MCP de FiveM
├── evals/                 casos de evaluación de la skill
├── tests/                 tests offline de los scripts
├── AGENTS.md · CHANGELOG.md · LICENSE
```

## Validación

Los scripts de la skill siguen usando solamente la biblioteca estándar de Python 3.8+. Las dependencias siguientes son exclusivas de las pruebas del repositorio:

```powershell
python -m unittest discover -s tests -v
# Opcional: ejecutar también los casos Lua y la compilación NUI (en un entorno de pruebas)
python -m pip install lupa==2.8
$env:FIVEM_REQUIRE_LUA_TESTS = '1'
$env:FIVEM_TEST_NUI_BUILD = '1'
python -m unittest discover -s tests -v
bun test ./tests/nui
```

En bash: `FIVEM_REQUIRE_LUA_TESTS=1 FIVEM_TEST_NUI_BUILD=1 python -m unittest discover -s tests -v`.

La suite básica no descarga dependencias. La compilación opcional usa Bun 1.4.2 y el `bun.lock` de la plantilla con `--frozen-lockfile`; requiere registro o caché. Lua usa `lupa.lua54`, con adaptadores que simulan fallos y cesiones de ejecución. Sin esos requisitos los casos opcionales figuran como omitidos; no deben contarse como aprobados.

`.github/workflows/skill-tests.yml` configura la matriz Python 3.8/3.12 y exige las pruebas Lua/NUI en un trabajo separado. La compilación y las pruebas de lógica no sustituyen CfxLua, oxmysql/InnoDB, CEF ni dos clientes reales de FiveM. Criterios y experimentos: [design-and-validation.md](skills/fivem-development/references/design-and-validation.md).

`audit.py --min` filtra la presentación: un hallazgo high/critical oculto sigue devolviendo error. El escáner incluye código compilado, pero excluye node_modules; no certifica dependencias. Los manifiestos calculados se reportan como no analizables; nunca se ejecutan para validarlos.

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
