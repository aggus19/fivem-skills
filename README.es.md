# FiveM Skills — `fivem-development`

[English](README.md) · **Español**

`fivem-development` es una [Agent Skill](https://agentskills.io/specification) abierta que da a los agentes de IA conocimiento actualizado y verificado contra fuentes primarias sobre desarrollo en FiveM (Cfx.re / GTA V), junto con herramientas en Python (solo biblioteca estándar) que inspeccionan un servidor real siempre de la misma forma. Está pensada para funcionar en cualquier servidor FiveM —ESX, QBCore, Qbox, ox_core, ND, vRP/Creative o standalone, con cualquier estructura de carpetas, en Windows o Linux, con o sin txAdmin— y con cualquier agente capaz de leer un `SKILL.md` o instrucciones de proyecto. Los datos de versiones son un baseline verificado el **2026-10-07** ([`references/versions.md`](skills/fivem-development/references/versions.md)).

## Qué hace

- **Crea** recursos adaptados al stack instalado (Lua, JS/TS, C#; NUI opcional con React/Vite), con validación del lado del servidor por defecto.
- **Modifica y convierte** recursos existentes respetando el framework, los dueños de los datos, la UI y el gestor de paquetes que ya se usan.
- **Depura** errores de scripts, fallos de carga, errores de entitlement de escrow y hitches a partir del log de la consola.
- **Optimiza** trabajo de cliente, servidor, NUI y base de datos con mediciones antes/después en lugar de reglas genéricas.
- **Audita** un recurso o un servidor completo: backdoors, inyección SQL, exploits por confiar en el cliente, duplicación de ítems/dinero, dependencias desactualizadas, `ensure`/`data_file` rotos y assets demasiado grandes, con un contrato de cobertura explícito ([`references/server-audit.md`](skills/fivem-development/references/server-audit.md)).

El Lua generado se entrega **sin comentarios explicativos**: `scaffold.py` los elimina de las plantillas, porque los scripts de cliente los descargan los jugadores y no deben explicar la lógica del servidor. Usá `--keep-comments` si querés la versión comentada para aprender.

## Inicio rápido desde tu servidor

Los scripts solo necesitan Python 3.8+. Ejecutalos desde la carpeta `resources/` de tu servidor (o desde la raíz) sin argumentos; encuentran solos la raíz del servidor, el cfg de arranque y los logs. Abajo, `<skill>` es la ruta donde pusiste `skills/fivem-development`.

```bash
cd /ruta/a/tu/servidor/resources

python <skill>/scripts/project.py      # inventario del servidor completo
python <skill>/scripts/logs.py         # problemas del log de la consola, agrupados y contados
python <skill>/scripts/surface.py --ledger ledger.md   # todos los puntos de entrada del servidor alcanzables desde el cliente
python <skill>/scripts/audit.py        # escaneo heurístico de seguridad / rendimiento / compatibilidad
python <skill>/scripts/manifest.py     # valida cada fxmanifest.lua debajo de la carpeta actual
```

- **`project.py`** — stack detectado (framework, inventario, target, driver de DB, voz, teléfono…), cadena de `exec` desde el cfg de arranque (el `cfgPath` de txAdmin si un perfil de txAdmin apunta a este servidor; si no, `server.cfg`), convars eliminadas o en conflicto, destinos de `ensure` vs carpetas reales (categorías expandidas), recursos duplicados o que nunca arrancan, versiones instaladas vs [`assets/baseline.json`](skills/fivem-development/assets/baseline.json) con `archivo:línea`, rutas de `data_file`, archivos de stream de más de 16 MiB y estado de git. Nunca imprime valores de convars.
- **`logs.py`** — encuentra solo `txData/<perfil>/logs/fxserver.log` (o `logs/*.log` junto al servidor) y lo lee en streaming, así que los logs grandes no son problema. Agrupa errores de script (recurso, `archivo:línea`, primer frame del stack), fallos de carga, recursos que no pudieron arrancar (incluido el entitlement de escrow), hitches de threads, queries lentas, assets de stream sobredimensionados, convars eliminadas o desconocidas, avisos de seguridad al arrancar y crashes. Los valores que parecen claves, tokens o webhooks se enmascaran.
- **`surface.py`** — lista todos los puntos de entrada del servidor alcanzables desde el cliente (net events, `lib.callback`, callbacks y comandos de ESX y QBCore/Qbox, wrappers de registro propios, exports, `SetHttpHandler`, `onNet` en JS, túneles de vRP/Creative) con los sinks que alcanza cada uno (dinero, ítems, vehículos, trabajos, escrituras SQL, coordenadas/buckets, spawns, `ExecuteCommand`…) en ESX, QBCore/Qbox, ND, ox_core y vRP/Creative, más etiquetas de riesgo de significado fijo. `--ledger` escribe un registro de cobertura en Markdown con IDs estables; `--shard K/N` lo reparte entre revisores en paralelo.
- **`audit.py`** y **`manifest.py`** — ambos usan la carpeta actual por defecto. `audit.py` reporta candidatos que hay que confirmar leyendo el código; `manifest.py` compara scripts, `files`, `ui_page`, dependencias y rutas de `data_file` con lo que hay en disco.

Después pedile a tu agente:

> Auditá mi servidor siguiendo `references/server-audit.md`.

El agente usa estas salidas como inventario, revisa cada fila del registro e informa los números de cobertura en lugar de muestrear.

Otros scripts: `natives.py` (busca y verifica natives, detecta natives inventadas o usadas del lado equivocado), `build_natives_catalog.py` (regenera el catálogo de natives), `scaffold.py` (crea un recurso; `--profile ox-shop`, `--nui`), `rcon.py` (envía un comando RCON a un servidor de desarrollo; la contraseña solo se lee de `FIVEM_RCON_PASSWORD`) y `server_info.py` (resume un servidor en marcha a partir de sus endpoints HTTP públicos).

```bash
python <skill>/scripts/natives.py update                 # descarga una vez la base oficial de natives (queda en caché)
python <skill>/scripts/natives.py show GetEntityCoords
python <skill>/scripts/natives.py check ./mi_recurso --strict
python <skill>/scripts/scaffold.py mi_recurso --out "./[custom]"
python <skill>/scripts/scaffold.py mi_tienda --profile ox-shop --nui --out "./[custom]"
```

## Usala con tu agente

La skill es la carpeta [`skills/fivem-development/`](skills/fivem-development/). Mantené juntos `SKILL.md`, `references/`, `scripts/` y `assets/`; los scripts resuelven sus datos relativos a su propia ubicación. La skill no es un recurso de FXServer: no lleva `ensure`.

### Claude Code

Como plugin (agrega los comandos `/fivem-new`, `/fivem-audit` y `/fivem-native` y el subagente de solo lectura `fivem-auditor`):

```bash
/plugin marketplace add aggus19/fivem-skills
/plugin install fivem-development@fivem-skills
```

Desde un clon local: `/plugin marketplace add ./ruta/a/fivem-skills` y el mismo comando de instalación.

Solo la skill: copiá `skills/fivem-development/` a `~/.claude/skills/fivem-development/` (todos los proyectos) o a `.claude/skills/fivem-development/` dentro de un proyecto.

### Agentes compatibles con el formato Agent Skills

Cualquier agente que cargue skills desde un `SKILL.md` con frontmatter `name`/`description` puede usar la carpeta tal cual: copiá `skills/fivem-development/` al directorio de skills de ese agente (por ejemplo, a nivel de proyecto, `.agents/skills/fivem-development/`). El directorio cambia según el agente; revisá la documentación de tu agente para saber cuál usa.

### Agentes sin soporte de skills

Para Codex, Cursor, Gemini CLI o cualquier otro agente que lea instrucciones de proyecto pero no skills, indicale [`AGENTS.md`](AGENTS.md) y [`skills/fivem-development/SKILL.md`](skills/fivem-development/SKILL.md) como instrucciones del proyecto (por ejemplo, referenciándolos desde tu archivo de instrucciones existente, sin reemplazar tus propias reglas). `SKILL.md` deriva al agente a la referencia que necesita, así que lee solo lo que la tarea requiere. Revisá la documentación de tu agente para ver cómo carga los archivos de instrucciones.

## Requisitos

- **Python 3.8+, solo biblioteca estándar.** No hace falta `pip install` para usar los scripts.
- **Funciona sin conexión**, salvo `natives.py update` / `build_natives_catalog.py`, que descargan la base oficial de natives de Cfx.re (caché en `~/.cache/fivem-skill` o `$FIVEM_SKILL_CACHE`). El catálogo completo de natives (7.379) también viene en `assets/natives/`.
- **Bun** (1.4.2 o Node/npm compatible) solo para compilar la plantilla NUI opcional.

## Qué incluye

| Área | Contenido |
|---|---|
| `SKILL.md` | Reglas no negociables (autoridad del servidor, no inventar natives ni APIs, adaptarse al stack instalado, rendimiento medido, niveles de evidencia, licencia de la plataforma), tabla de ruteo a referencias y flujos de trabajo (crear, modificar, auditar un recurso, auditar un servidor, convertir, optimizar). |
| `references/` | Plataforma (versiones, server.cfg, convars, txAdmin, OneSync, GTA V Enhanced, logs de consola), scripting (fxmanifest, runtimes, eventos, natives, NUI, tooling, debugging), librerías de overextended (ox_lib, oxmysql, ox_inventory, ox_target, ox_core), frameworks (Qbox, ESX Legacy, QBCore, ND/vRP, bridge multi-framework), gameplay y sistemas RP, seguridad, anticheat, checklists de auditoría, rendimiento y escalado, licencias. |
| `assets/` | Catálogo de natives por namespace, `baseline.json`, plantillas (Lua sin dependencias, perfil opcional `ox-shop` con bridge de frameworks, NUI React 19 + Vite + TypeScript con target CEF 103), configs (LuaLS, selene, StyLua, `server.cfg.example`, workflow de GitHub Actions). |
| `scripts/` | Las herramientas descritas arriba y el helper compartido `resource_files.py`. Los manifiestos se analizan estáticamente y nunca se ejecutan. |
| Plugin de Claude Code | `commands/`, `agents/`, `.claude-plugin/`. |
| `evals/`, `tests/` | Escenarios de evaluación (especificaciones, no ejecuciones de agentes) y tests offline con fixtures. |

## Qué está verificado

```bash
python -m unittest discover -s tests -v
```

En Windows con Python 3.12 la suite ejecuta hoy **119 tests: 87 pasan y 32 se omiten**. Los omitidos son los tests opcionales de lógica Lua 5.4 (requieren `lupa`) y la compilación real de la NUI (requiere Bun); se habilitan con `FIVEM_REQUIRE_LUA_TESTS=1` y `FIVEM_TEST_NUI_BUILD=1`. Los omitidos no cuentan como aprobados. El workflow de GitHub Actions corre Python 3.8 y 3.12 y los trabajos Lua/NUI por separado.

Estos tests cubren los scripts, las plantillas y lógica simulada. No son tests de integración con FXServer ni con una base de datos real, ni benchmarks de rendimiento, y no se afirma ninguna mejora de velocidad en ejecución. Ver [`design-and-validation.md`](skills/fivem-development/references/design-and-validation.md) para los niveles de evidencia.

## Privacidad y seguridad

- Los scripts son **de solo lectura por defecto**. Solo escriben archivos `scaffold.py` (crea un recurso donde indiques), `surface.py --ledger` (escribe el archivo de registro que nombres) y las herramientas de natives (`natives.py update` escribe su caché; `build_natives_catalog.py` regenera `assets/natives/`).
- Los scripts **nunca imprimen secretos**: `project.py` no muestra valores de convars, `logs.py` enmascara lo que parece una clave, token o webhook, y `rcon.py` lee su contraseña solo de una variable de entorno.
- **Sin telemetría.** El único acceso a red es la descarga de la base de natives y, si los ejecutás, `rcon.py` / `server_info.py` contra un servidor que vos elegís (`rcon.py` rechaza hosts no locales salvo con `--allow-remote`).

## Uso responsable

Las funciones de auditoría son para **seguridad defensiva**: revisar servidores y recursos propios o que tenés autorización para revisar. La skill respeta el Creator Platform License Agreement de Cfx.re: nada de saltear el escrow, recursos filtrados, apuestas con dinero real, loot boxes, venta de moneda ni cobros fuera de Tebex. Ver [`references/licensing-and-policy.md`](skills/fivem-development/references/licensing-and-policy.md) y los términos oficiales en https://fivem.net/terms.

## Contribuir

- Los datos de versiones envejecen. Volvé a verificarlos con la sección "How to re-verify" de [`references/versions.md`](skills/fivem-development/references/versions.md), actualizá la fecha del baseline (`metadata.baseline-date` en `SKILL.md`) y mantené sincronizados `assets/baseline.json` y `versions.md`.
- Cada detección nueva en `audit.py`, `surface.py`, `project.py` o `logs.py` necesita un fixture en `tests/fixtures/` y un test.
- Los scripts siguen siendo Python 3.8+ con biblioteca estándar; `SKILL.md` queda por debajo de 500 líneas con referencias a un solo nivel de profundidad (ver [`AGENTS.md`](AGENTS.md)).
- Corré `python -m unittest discover -s tests -v` y anotá los cambios en [`CHANGELOG.md`](CHANGELOG.md).

## Fuentes principales

- Docs de Cfx.re: https://docs.fivem.net/docs/ · natives: https://docs.fivem.net/natives/ · descarga del servidor: https://docs.fivem.net/docs/server-download/
- overextended: https://overextended.dev/docs · Qbox: https://docs.qbox.re · ESX: https://docs.esx-framework.org/en · QBCore: https://qbcore.org/docs
- txAdmin: https://github.com/citizenfx/txAdmin/releases · PLA: https://fivem.net/terms
- Agent Skills: https://agentskills.io/specification · Plugins de Claude Code: https://code.claude.com/docs/en/plugins-reference

## Licencia

[MIT](LICENSE). FiveM, Cfx.re y GTA V son marcas de sus respectivos dueños. Este proyecto no está afiliado a Rockstar Games, Take-Two ni Cfx.re.
