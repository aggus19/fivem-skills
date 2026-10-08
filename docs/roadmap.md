# Plan de robustecimiento de la skill FiveM

Revisión: 2026-10-08. Objetivo: una skill general que se adapte al proyecto y a la
solicitud, razone sobre sus mecanismos y pueda demostrar qué comprobó. No requiere
un framework, lenguaje, inventario, interfaz o motor de DB concreto.

## Viabilidad y criterio de calidad

Es viable como método de descubrimiento, diseño, implementación, diagnóstico y
validación. No es viable prometer compatibilidad automática con cualquier fork,
seguridad absoluta o ausencia de hitches por elegir una versión. Cada recomendación
debe indicar contexto, fuente, fecha y nivel de evidencia cuando corresponda.

La base de confiabilidad ya incorporó comprobadores sensibles al manifiesto,
pruebas de fallos/concurrencia de lógica Lua, compilación NUI con Bun y separación
entre ejemplos y servicios completos. El historial exacto de ejecuciones está en
[CHANGELOG.md](../CHANGELOG.md). Las etapas siguientes amplían esa base.

## Etapas y condiciones de cierre

| Etapa | Trabajo | Condición para darla por validada | Estado |
|---|---|---|---|
| 1. Adaptación al proyecto | Descubrir recursos activos, versiones, forks, contratos, propietarios de datos y runtimes; dependencias mínimas | Casos standalone, ox, framework personalizado y proyecto existente conservan su arquitectura; skill instalada en otra ruta funciona | Guía y generador mínimo implementados; ambos perfiles y ubicación alternativa comprobados localmente; evaluación de agentes pendiente |
| 2. Seguridad de operaciones | Seguir eventos/callbacks/exports/comandos/NUI/HTTP hasta efectos; autorización, límites, repetición, concurrencia y recuperación | Pruebas de intentos inválidos y fallos en cada frontera; ninguna vía alternativa evade el propietario | Matriz y contratos incorporados; pruebas de lógica existentes; falta integración por stack |
| 3. Rendimiento cliente/servidor/NUI/red | Perfiles reproducibles, trabajo por frame, colas, GC, entidades, mensajes y ciclo de vida | Comparaciones con igual carga, métricas y variación; funcionalidad conservada; regresiones documentadas | Método incorporado; mediciones FiveM pendientes |
| 4. DB e hitches | Versiones soportadas actuales, SQL real, planes/índices, transacciones, colas, durabilidad y causa del retraso | Migraciones/restore y pruebas de concurrencia en motores reales; correlación DB/FXServer/host; sin recetas por slots | Fuentes y recomendaciones revisadas; pruebas con motor real pendientes |
| 5. Integración y casos de uso | Matriz representativa de stacks/runtimes; reinicios, desconexiones, dependencias y errores de infraestructura | Evidencia de arranque/operación/recuperación en versiones fijadas; límites de cobertura explícitos | Pendiente de entorno FXServer/DB/clientes de prueba |
| 6. Evaluación y mantenimiento | Evaluar respuestas/artefactos ante solicitudes reales; refrescar fuentes y retirar consejos obsoletos | Casos ejecutados con resultados revisables; correcciones basadas en fallos; fechas/commits y regresiones | Casos ampliados; todavía no ejecutados como evaluación de agentes |

Estas etapas se relacionan: una optimización que permite duplicar dinero no pasa,
y una protección que crea colas ilimitadas tampoco. Ampliar documentación no cierra
por sí solo una etapa de integración o rendimiento.

## Matriz representativa para la integración

No se pretende probar el producto cartesiano de todos los servidores. Se fijan
combinaciones y se amplían cuando una solicitud o un fallo aporta un caso distinto.

| Eje | Casos mínimos propuestos |
|---|---|
| Arquitectura | Standalone sin DB; Qbox; ESX; QBCore con inventario compatible; un adaptador personalizado |
| Lenguaje | CfxLua; recurso JS/TS; recurso C# con runtime correspondiente |
| Plataforma | Windows/Linux según soporte; Legacy como entorno de prueba definido; Enhanced separado por diferencias reales |
| Persistencia | MariaDB LTS y MySQL LTS cuando el SQL sea compatible; documentar incompatibilidades esperadas |
| Cliente | NUI cerrada/abierta/recargada, inicio temprano, distintas cargas/FPS, varios clientes en zona densa |
| Fallos | Cantidad inválida, permisos/propiedad incorrectos, repetición, acciones concurrentes, desconexión y cambio de personaje, timeout, resultado desconocido y reinicio |
| Carga | Reposo, interacción normal, ingresos simultáneos, guardado periódico, concentración de entidades y ejecución prolongada |

Usar datos sintéticos o anonimizados y un entorno aislado. Registrar versiones,
configuración, hardware, datos y carga. Separar fallos del producto, del adaptador y
del entorno. Los fixtures no sustituyen los contratos del framework instalado.

## Próxima tanda de evidencia

1. Ejecutar los escenarios ampliados de `evals/evals.json` sobre proyectos de prueba
   con respuestas y artefactos conservados. No confundirlos con la suite unitaria.
2. Construir fixtures SQL propios para transferencias, bloqueo, rollback y resultado
   de commit desconocido; ejecutarlos en las versiones elegidas de motores reales.
3. Integrar un recurso de prueba sin economía y después operaciones de un propietario
   real de inventario/cuentas. Comprobar reinicio y recuperación antes de ampliar stacks.
4. Capturar un problema reproducible de scripts, uno de NUI y uno de consultas/colas;
   comparar cambios y publicar resultados con sus límites. Un resultado que empeora
   o no cambia también sirve para corregir la recomendación.

## Mantenimiento de recomendaciones

- Para «qué versión usar hoy», consultar nuevamente releases, disponibilidad GA,
  soporte Community/Enterprise/distribución y compatibilidad del proyecto.
- Para APIs, inspeccionar la versión instalada y usar documentación/código coincidente.
- Para cifras de rendimiento, guardar metodología y mediciones; no generalizar una
  prueba local a todos los frameworks, hardware o cantidades de jugadores.
- Mantener `SKILL.md` como entrada breve con referencias por tarea; no obligar a cargar
  todo el catálogo en una corrección pequeña ni duplicar tablas de versiones.
- Cada entrega declara qué está documentado, revisado en código, probado con dobles,
  integrado o medido. Las limitaciones pendientes permanecen visibles.
