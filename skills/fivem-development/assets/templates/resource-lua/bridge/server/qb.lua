-- QBCore (github.com/qbcore-fivem/qb-core, 2026 refactor).
-- Items go through qb-inventory exports (CanAddItem/AddItem/RemoveItem/GetItemCount/HasItem).
-- ox_inventory dropped QBCore support in v2.42.0, so it is never used here.
local QBCore = exports['qb-core']:GetCoreObject()
local B = {}

function B.GetPlayer(src) return QBCore.Functions.GetPlayer(src) end

function B.GetIdentifier(src)
    local p = B.GetPlayer(src)
    return p and p.PlayerData.citizenid
end

function B.GetName(src)
    local p = B.GetPlayer(src)
    if not p then return GetPlayerName(src) end
    local ci = p.PlayerData.charinfo
    return ('%s %s'):format(ci.firstname, ci.lastname)
end

function B.GetJob(src)
    local p = B.GetPlayer(src)
    if not p then return nil end
    local j = p.PlayerData.job
    return { name = j.name, grade = j.grade.level, label = j.label, onDuty = j.onduty }
end

function B.HasJob(src, name, minGrade)
    local job = B.GetJob(src)
    return job ~= nil and job.name == name and job.grade >= (minGrade or 0)
end

function B.GetMoney(src, account)
    local p = B.GetPlayer(src)
    return p and p.Functions.GetMoney(account) or 0
end

function B.AddMoney(src, account, amount, reason)
    local p = B.GetPlayer(src)
    return p ~= nil and p.Functions.AddMoney(account, amount, reason) == true
end

function B.RemoveMoney(src, account, amount, reason)
    local p = B.GetPlayer(src)
    return p ~= nil and p.Functions.RemoveMoney(account, amount, reason) == true
end

local inv = exports['qb-inventory'] -- qb-inventory 2.x exports

function B.CanCarry(src, item, count)
    return inv:CanAddItem(src, item, count) == true
end

function B.AddItem(src, item, count, metadata)
    if not B.CanCarry(src, item, count) then return false end
    return inv:AddItem(src, item, count, false, metadata, GetInvokingResource() or 'bridge') == true
end

function B.RemoveItem(src, item, count)
    if (inv:GetItemCount(src, item) or 0) < count then return false end
    return inv:RemoveItem(src, item, count, false, 'bridge') == true
end

function B.HasItem(src, item, count)
    return inv:HasItem(src, item, count or 1) == true
end

function B.Notify(src, msg, type) TriggerClientEvent('QBCore:Notify', src, msg, type) end
function B.RegisterUsableItem(name, cb) QBCore.Functions.CreateUseableItem(name, cb) end

return B
