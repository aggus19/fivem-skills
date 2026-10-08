-- Test fixture: benign look-alikes of the patterns in ioc_resource. audit.py must not flag the new rules here.
PerformHttpRequest('https://api.fivemanage.com/x', function() end)
local f = io.open('data.txt', 'r')
local KEY = GetConvar('sv_licenseKey', '')
local TOKEN = GetConvar('bot_token', '')
print(debug.traceback())
local name = GetCurrentResourceName()
local cfg = _G['MyGlobal']
AddStateBagChangeHandler('vip', nil, function(bagName, key, value, _, replicated) end)

RegisterNetEvent('clean:ping')
AddEventHandler('clean:ping', function()
    local src = source
    print(src)
end)
