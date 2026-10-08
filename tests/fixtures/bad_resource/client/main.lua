ESX = nil
TriggerEvent('esx:getSharedObject', function(obj) ESX = obj end)
while true do
  local p = GetPlayerPed(-1)
end
RegisterCommand('sell', function() TriggerServerEvent('shop:sellItem', 'bread', 500) end)
local x = GetPlayerIdentifierByType(1, 'license')
