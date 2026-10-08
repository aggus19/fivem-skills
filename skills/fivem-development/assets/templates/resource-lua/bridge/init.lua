-- Framework adapter. Business logic only calls Bridge.*; never framework APIs directly.
-- Detection order matters: qbx_core `provide`s 'qb-core', so check it first.
Bridge = {}

local function detectFramework()
    local forced = GetConvar('{{RESOURCE_NAME}}:framework', 'auto')
    if forced ~= 'auto' then return forced end
    if GetResourceState('qbx_core'):find('start') then return 'qbx' end
    if GetResourceState('es_extended'):find('start') then return 'esx' end
    if GetResourceState('qb-core'):find('start') then return 'qb' end
    return 'standalone'
end

Bridge.framework = detectFramework()
Bridge.hasOxInventory = GetResourceState('ox_inventory'):find('start') ~= nil
Bridge.hasOxTarget = GetResourceState('ox_target'):find('start') ~= nil

local side = IsDuplicityVersion() and 'server' or 'client'
local ok, impl = pcall(require, ('bridge.%s.%s'):format(side, Bridge.framework))
if not ok then
    lib.print.error(('bridge %s/%s failed to load: %s'):format(side, Bridge.framework, impl))
    impl = require(('bridge.%s.standalone'):format(side))
end

for k, v in pairs(impl) do Bridge[k] = v end

if side == 'client' and not Bridge.Notify then
    function Bridge.Notify(msg, type) lib.notify({ description = msg, type = type or 'inform' }) end
end
lib.print.info(('framework: %s (ox_inventory: %s, ox_target: %s)'):format(Bridge.framework, Bridge.hasOxInventory, Bridge.hasOxTarget))
