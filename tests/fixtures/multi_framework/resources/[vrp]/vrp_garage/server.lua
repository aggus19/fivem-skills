local Tunnel = module('vrp', 'lib/Tunnel')
local Proxy = module('vrp', 'lib/Proxy')
vRP = Proxy.getInterface('vRP')

cRP = {}
Tunnel.bindInterface('vrp_garage', cRP)

function cRP.sellVehicle(price)
    local source = source
    local user_id = vRP.getUserId(source)
    vRP.giveBankMoney(user_id, price)
end

function cRP.vehicleList()
    return {}
end
