-- Server-authoritative shop: who, allowed, where, what, how often (references/security.md §2).

local RESOURCE = GetCurrentResourceName()
local cooldowns = {}
local busy, sessions = {}, {}
local purchase = require 'server.purchase'

local function log(src, message)
    lib.print.info(('[%s] %s (%s): %s'):format(RESOURCE, GetPlayerName(src), Bridge.GetIdentifier(src), message))
    if ServerConfig.Webhook ~= '' then
        PerformHttpRequest(ServerConfig.Webhook, function() end, 'POST',
            json.encode({ content = ('%s: %s'):format(GetPlayerName(src), message) }),
            { ['Content-Type'] = 'application/json' })
    end
end

local function isNearShop(src, shop)
    if GetPlayerRoutingBucket(src) ~= ServerConfig.ShopBucket then return false end
    local ped = GetPlayerPed(src)
    if ped == 0 or not DoesEntityExist(ped) then return false end
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

    -- Configure a durable recovery/operation service before enabling this example.
    if not ServerConfig.PurchasesEnabled then return false, 'unavailable' end

    -- 1. who
    if not Bridge.GetPlayer(src) then return false, 'invalid' end

    -- 4. what (types, ranges, whitelists) — checked early to reject garbage cheaply
    if type(shopId) ~= 'string' or type(item) ~= 'string' or type(count) ~= 'number' then return false, 'invalid' end
    if #shopId > 64 or #item > 64 then return false, 'invalid' end
    if count ~= count or count % 1 ~= 0 or count < 1 or count > ServerConfig.MaxPerPurchase then return false, 'invalid' end

    local shop = Config.Shops[shopId]
    if not shop or not lib.table.contains(shop.items, item) then return false, 'invalid' end
    local price = ServerConfig.Prices[item]
    if type(price) ~= 'number' or price ~= price or price % 1 ~= 0 or price <= 0
        or price > ServerConfig.MaxTransaction / count then return false, 'invalid' end

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

    local character = Bridge.GetIdentifier(src)
    if not character or busy[character] then return false, 'busy' end
    sessions[src] = sessions[src] or {}
    local session, token = sessions[src], {}
    busy[character] = token
    local total, unresolved = price * count, false
    local function current()
        return sessions[src] == session and Bridge.GetIdentifier(src) == character
    end
    local called, ok, reason = pcall(function()
        if not Bridge.CanCarry(src, item, count) then return false, 'cannot_carry' end
        if not current() or not isNearShop(src, shop) then return false, 'invalid' end
        return purchase({
            isCurrent = current,
            debit = function() return Bridge.RemoveMoney(src, ServerConfig.Account, total, RESOURCE .. ':buy') end,
            grant = function() return Bridge.AddItem(src, item, count) end,
            refund = function() return Bridge.AddMoney(src, ServerConfig.Account, total, RESOURCE .. ':refund') end,
            recovery = function(stage)
                unresolved = true
                -- App-owned contract, not a framework export. Persist and alert; never auto-regrant.
                ServerConfig.RecordRecovery({ character = character, shop = shopId, item = item,
                    count = count, total = total, account = ServerConfig.Account, stage = stage })
            end,
        })
    end)
    if not called then
        unresolved = true
        lib.print.error(('purchase exception for %s; manual reconciliation required: %s'):format(character, ok))
    end
    -- Retain a blocked character after an ambiguous mutation, even after disconnect.
    if not unresolved and busy[character] == token then busy[character] = nil end
    if unresolved then return false, 'recovery_required' end
    if ok then log(src, ('bought %sx %s for $%s at %s'):format(count, item, total, shopId)) end
    return ok, reason
end)

AddEventHandler('playerDropped', function()
    cooldowns[source] = nil
    sessions[source] = nil
end)
