-- ESX Legacy (es_extended 1.11+). Accounts: 'money' (cash), 'bank', 'black_money'.
local ESX = exports.es_extended:getSharedObject()
local inv = Bridge.hasOxInventory and require 'bridge.server.oxinventory' or nil
local B = {}

local accountMap = { cash = 'money', bank = 'bank', black_money = 'black_money' }
local function acc(account) return accountMap[account] or account end

function B.GetPlayer(src) return ESX.GetPlayerFromId(src) end

function B.GetIdentifier(src)
    local x = B.GetPlayer(src)
    return x and x.getIdentifier()
end

function B.GetName(src)
    local x = B.GetPlayer(src)
    return x and x.getName() or GetPlayerName(src)
end

function B.GetJob(src)
    local x = B.GetPlayer(src)
    if not x then return nil end
    local j = x.getJob()
    return { name = j.name, grade = j.grade, label = j.label, onDuty = j.onDuty ~= false }
end

function B.HasJob(src, name, minGrade)
    local job = B.GetJob(src)
    return job ~= nil and job.name == name and job.grade >= (minGrade or 0)
end

function B.GetMoney(src, account)
    local x = B.GetPlayer(src)
    local a = x and x.getAccount(acc(account))
    return a and a.money or 0
end

function B.AddMoney(src, account, amount, reason)
    local x = B.GetPlayer(src)
    if not x then return false end
    x.addAccountMoney(acc(account), amount, reason)
    return true
end

function B.RemoveMoney(src, account, amount, reason)
    local x = B.GetPlayer(src)
    if not x or B.GetMoney(src, account) < amount then return false end
    x.removeAccountMoney(acc(account), amount, reason)
    return true
end

if inv then
    B.AddItem, B.RemoveItem, B.HasItem, B.CanCarry = inv.AddItem, inv.RemoveItem, inv.HasItem, inv.CanCarry
else
    function B.CanCarry(src, item, count)
        local x = B.GetPlayer(src)
        return x ~= nil and x.canCarryItem(item, count)
    end

    function B.AddItem(src, item, count)
        local x = B.GetPlayer(src)
        if not x or not x.canCarryItem(item, count) then return false end
        x.addInventoryItem(item, count)
        return true
    end

    function B.RemoveItem(src, item, count)
        local x = B.GetPlayer(src)
        local it = x and x.getInventoryItem(item)
        if not it or it.count < count then return false end
        x.removeInventoryItem(item, count)
        return true
    end

    function B.HasItem(src, item, count)
        local x = B.GetPlayer(src)
        local it = x and x.getInventoryItem(item)
        return it ~= nil and it.count >= (count or 1)
    end
end

function B.Notify(src, msg, type)
    local x = B.GetPlayer(src)
    if x then x.showNotification(msg, type) end
end

function B.RegisterUsableItem(name, cb) ESX.RegisterUsableItem(name, cb) end

return B
