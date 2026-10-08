-- No framework: identity = Rockstar license, no money/jobs (extend with your own tables if needed).
local inv = Bridge.hasOxInventory and require 'bridge.server.oxinventory' or nil
local B = {}

local function unsupported(name)
    lib.print.warn(('Bridge.%s is not supported without a framework'):format(name))
    return false
end

function B.GetPlayer(src) return GetPlayerName(src) and { source = src } or nil end
function B.GetIdentifier(src) return GetPlayerIdentifierByType(src, 'license') end
function B.GetName(src) return GetPlayerName(src) end
function B.GetJob() return nil end
function B.HasJob() return false end
function B.GetMoney() return 0 end
function B.AddMoney() return unsupported('AddMoney') end
function B.RemoveMoney() return unsupported('RemoveMoney') end

if inv then
    B.AddItem, B.RemoveItem, B.HasItem, B.CanCarry = inv.AddItem, inv.RemoveItem, inv.HasItem, inv.CanCarry
else
    function B.AddItem() return unsupported('AddItem') end
    function B.RemoveItem() return unsupported('RemoveItem') end
    function B.HasItem() return false end
    function B.CanCarry() return false end
end

function B.Notify(src, msg, type)
    TriggerClientEvent('ox_lib:notify', src, { description = msg, type = type or 'inform' })
end

function B.RegisterUsableItem() return unsupported('RegisterUsableItem') end

return B
