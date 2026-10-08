-- Fixture: validated purchase. Server price, integer amount, balance read, cooldown, result checked.
local PRICE <const> = 100
local cooldowns = {}

lib.callback.register('eco_ok:buy', function(source, data)
    local player = ESX.GetPlayerFromId(source)
    local now = GetGameTimer()
    if cooldowns[source] and now - cooldowns[source] < 1000 then return false end
    cooldowns[source] = now
    local quantity = math.tointeger(tonumber(data and data.quantity))
    if not quantity or quantity < 1 or quantity > 10 then return false end
    local total = PRICE * quantity
    if player.getAccount('bank').money < total then return false end
    player.removeAccountMoney('bank', total)
    player.addInventoryItem('bread', quantity)
    return true
end)
