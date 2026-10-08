-- Server-authoritative shop: who, allowed, where, what, how often (references/security.md §2).

local RESOURCE = GetCurrentResourceName()
local cooldowns = {}

local function log(src, message)
    lib.print.info(('[%s] %s (%s): %s'):format(RESOURCE, GetPlayerName(src), Bridge.GetIdentifier(src), message))
    if ServerConfig.Webhook ~= '' then
        PerformHttpRequest(ServerConfig.Webhook, function() end, 'POST',
            json.encode({ content = ('%s: %s'):format(GetPlayerName(src), message) }),
            { ['Content-Type'] = 'application/json' })
    end
end

local function isNearShop(src, shop)
    local ped = GetPlayerPed(src)
    if ped == 0 then return false end
    return #(GetEntityCoords(ped) - shop.coords) <= ServerConfig.MaxDistance
end

lib.callback.register(RESOURCE .. ':server:getPrices', function(source, shopId)
    local shop = type(shopId) == 'string' and Config.Shops[shopId]
    if not shop then return nil end

    local prices = {}
    for _, item in ipairs(shop.items) do prices[item] = ServerConfig.Prices[item] end
    return prices
end)

lib.callback.register(RESOURCE .. ':server:buy', function(source, shopId, item, count)
    local src = source

    -- 1. who
    if not Bridge.GetPlayer(src) then return false, 'invalid' end

    -- 4. what (types, ranges, whitelists) — checked early to reject garbage cheaply
    if type(shopId) ~= 'string' or type(item) ~= 'string' or type(count) ~= 'number' then return false, 'invalid' end
    count = math.floor(count)
    if count < 1 or count > ServerConfig.MaxPerPurchase or count ~= count then return false, 'invalid' end

    local shop = Config.Shops[shopId]
    if not shop or not lib.table.contains(shop.items, item) then return false, 'invalid' end
    local price = ServerConfig.Prices[item]
    if not price then return false, 'invalid' end

    -- 5. how often
    local now = os.time()
    if (cooldowns[src] or 0) > now then return false, 'cooldown' end
    cooldowns[src] = now + ServerConfig.PurchaseCooldown

    -- 3. where
    if not isNearShop(src, shop) then
        log(src, ('tried to buy %sx %s far from shop %s'):format(count, item, shopId))
        return false, 'too_far'
    end

    -- 2. allowed (example: no restriction; add Bridge.HasJob(src, 'x') checks here if needed)

    -- transaction: check capacity, take money FIRST, then give the item; refund on failure
    if not Bridge.CanCarry(src, item, count) then return false, 'cannot_carry' end

    local total = price * count
    if not Bridge.RemoveMoney(src, ServerConfig.Account, total, RESOURCE .. ':buy') then
        return false, 'not_enough_money'
    end

    if not Bridge.AddItem(src, item, count) then
        Bridge.AddMoney(src, ServerConfig.Account, total, RESOURCE .. ':refund')
        return false, 'cannot_carry'
    end

    log(src, ('bought %sx %s for $%s at %s'):format(count, item, total, shopId))
    return true, 'bought'
end)

AddEventHandler('playerDropped', function()
    cooldowns[source] = nil
end)
