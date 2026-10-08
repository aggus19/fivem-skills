-- Fixture: each handler reproduces one exploit class from a real audit. Do not copy.
local players_time = {}

-- credit-before-guard + client-position: pays from a client distance, time check after paying
lib.callback.register('eco:job:payment', function(source, data)
    local player = ESX.GetPlayerFromId(source)
    local amount = math.floor(data.distance_delivery * 10)
    player.addAccountMoney('bank', amount)
    if players_time[source] then
        if os.time() - players_time[source] < 5 then
            return false
        end
    end
    players_time[source] = os.time()
    return true
end)

-- not-eq-precedence: the permission check never rejects
lib.callback.register('eco:event:create', function(source, event)
    local player = ESX.GetPlayerFromId(source)
    if not player.permission_level == 5 then return false end
    MySQL.insert('INSERT INTO events (owner, data) VALUES (?, ?)', { player.identifier, json.encode(event) })
    return true
end)

-- client-target: moves players chosen by the client into a routing bucket
lib.callback.register('eco:switchBucket', function(source, id, passengers)
    for _, target in ipairs(passengers) do
        SetPlayerRoutingBucket(target, id)
    end
    SetPlayerRoutingBucket(source, id)
end)

-- non-integer-amount + no-balance-check: client quantity, no balance read
lib.callback.register('eco:shop:buy', function(source, data)
    local player = ESX.GetPlayerFromId(source)
    local quantity = tonumber(data.quantity)
    player.removeAccountMoney('bank', 100 * quantity)
    player.addInventoryItem('bread', quantity)
end)

-- unchecked-removal: pays even when the removal failed
lib.callback.register('eco:sell', function(source, data)
    local player = ESX.GetPlayerFromId(source)
    local count = data.count
    exports.ox_inventory:RemoveItem(source, 'wood', count)
    player.addAccountMoney('bank', count * 50)
end)

-- client-value-in-sink through a helper reached via an alias (ox_fuel pattern)
local function defaultPayment(playerId, price)
    return exports.ox_inventory:RemoveItem(playerId, 'money', price)
end
local payMoney = defaultPayment

RegisterNetEvent('eco:fuel:pay', function(price)
    local src = source
    if not payMoney(src, price) then return end
end)

-- split registration form without `source`
RegisterServerEvent('eco:broadcast')
AddEventHandler('eco:broadcast', function(message)
    TriggerClientEvent('eco:message', -1, message)
end)
