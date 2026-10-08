-- Qbox (qbx_core >= 1.22): exports API; Player.Functions.* is deprecated.
local qbx = exports.qbx_core
local inv = require 'bridge.server.oxinventory' -- Qbox always runs ox_inventory
local B = {}

function B.GetPlayer(src) return qbx:GetPlayer(src) end

function B.GetIdentifier(src)
    local p = qbx:GetPlayer(src)
    return p and p.PlayerData.citizenid
end

function B.GetName(src)
    local p = qbx:GetPlayer(src)
    if not p then return GetPlayerName(src) end
    local ci = p.PlayerData.charinfo
    return ('%s %s'):format(ci.firstname, ci.lastname)
end

function B.GetJob(src)
    local p = qbx:GetPlayer(src)
    if not p then return nil end
    local j = p.PlayerData.job
    return { name = j.name, grade = j.grade.level, label = j.label, onDuty = j.onduty }
end

function B.HasJob(src, name, minGrade)
    local job = B.GetJob(src)
    return job ~= nil and job.name == name and job.grade >= (minGrade or 0)
end

function B.GetMoney(src, account) return qbx:GetMoney(src, account) or 0 end
function B.AddMoney(src, account, amount, reason) return qbx:AddMoney(src, account, amount, reason) == true end
function B.RemoveMoney(src, account, amount, reason) return qbx:RemoveMoney(src, account, amount, reason) == true end

B.AddItem, B.RemoveItem, B.HasItem, B.CanCarry = inv.AddItem, inv.RemoveItem, inv.HasItem, inv.CanCarry

function B.Notify(src, msg, type) qbx:Notify(src, msg, type) end
function B.RegisterUsableItem(name, cb) qbx:CreateUseableItem(name, cb) end

return B
