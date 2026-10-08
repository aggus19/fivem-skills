# {{RESOURCE_NAME}}

Dependency-free Lua starting point. Implement the requested feature using the
project's installed framework, inventory, database driver and UI when needed.
This skeleton contains no economy, network handlers, database or idle loops.

Add `ensure {{RESOURCE_NAME}}` to the server configuration after implementing and
testing the feature. Declare only the dependencies it actually uses in the manifest.
Remove unused sides when the feature is client-only or server-only.

If generated with `--nui`, build in `web/` with `bun install --frozen-lockfile`
and `bun run --bun build`. The demo opens with `/{{RESOURCE_NAME}}_ui`.
The included NUI callbacks manage presentation only; its `action` callback does
not authorize or perform a server operation. Integrate a validated server endpoint
for real actions. Match an existing project's package manager and lockfile.

Run the skill's native, manifest and audit checks, then verify resource start/stop,
the real feature, and failure cases in FXServer. Static checks are not runtime proof.
