-- Example feature: a shop. The client only shows UI and sends *intent* (shop, item, count).
-- Prices, validation and the transaction happen on the server (server/main.lua).

local RESOURCE = GetCurrentResourceName()
local blips, zones, points = {}, {}, {}

local function openShop(shopId)
    local shop = Config.Shops[shopId]
    local prices = lib.callback.await(RESOURCE .. ':server:getPrices', false, shopId)
    if not prices then return end

    local options = {}
    for _, item in ipairs(shop.items) do
        options[#options + 1] = {
            title = item,
            description = ('$%s'):format(prices[item] or '?'),
            icon = 'basket-shopping',
            onSelect = function()
                local input = lib.inputDialog(locale('buy_title'), {
                    { type = 'number', label = locale('amount'), min = 1, max = 20, default = 1, required = true },
                })
                if not input then return end

                local ok, reason = lib.callback.await(RESOURCE .. ':server:buy', false, shopId, item, input[1])
                lib.notify({ description = locale(reason), type = ok and 'success' or 'error' })
            end,
        }
    end

    lib.registerContext({ id = RESOURCE .. '_shop', title = shop.label, options = options })
    lib.showContext(RESOURCE .. '_shop')
end

local function setupShops()
    for shopId, shop in pairs(Config.Shops) do
        if shop.blip then
            local blip = AddBlipForCoord(shop.coords.x, shop.coords.y, shop.coords.z)
            SetBlipSprite(blip, shop.blip.sprite)
            SetBlipColour(blip, shop.blip.colour)
            SetBlipScale(blip, shop.blip.scale)
            SetBlipAsShortRange(blip, true)
            BeginTextCommandSetBlipName('STRING')
            AddTextComponentSubstringPlayerName(shop.label)
            EndTextCommandSetBlipName(blip)
            blips[#blips + 1] = blip
        end

        if Bridge.hasOxTarget then
            zones[#zones + 1] = exports.ox_target:addSphereZone({
                coords = shop.coords,
                radius = 1.5,
                debug = Config.Debug,
                options = {
                    {
                        name = RESOURCE .. ':open:' .. shopId,
                        label = locale('shop_open'),
                        icon = 'fa-solid fa-store',
                        distance = Config.InteractDistance,
                        onSelect = function() openShop(shopId) end,
                    },
                },
            })
        else
            -- Fallback without ox_target: one optimised ox_lib point per shop, input read only while inside.
            points[#points + 1] = lib.points.new({
                coords = shop.coords,
                distance = Config.InteractDistance,
                onEnter = function() lib.showTextUI('[E] ' .. locale('shop_open')) end,
                onExit = function() lib.hideTextUI() end,
                nearby = function()
                    if IsControlJustReleased(0, 38) then openShop(shopId) end -- 38 = E
                end,
            })
        end
    end
end

CreateThread(setupShops)

AddEventHandler('onResourceStop', function(resource)
    if resource ~= RESOURCE then return end
    for _, blip in ipairs(blips) do RemoveBlip(blip) end
    for _, id in ipairs(zones) do exports.ox_target:removeZone(id) end
    for _, point in ipairs(points) do point:remove() end
    lib.hideTextUI()
end)
