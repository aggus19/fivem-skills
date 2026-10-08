local ESX = exports.es_extended:getSharedObject()
local B = {}

local function normJob(j)
    return j and { name = j.name, grade = j.grade, label = j.label, onDuty = j.onDuty ~= false } or nil
end

function B.GetPlayerData() return ESX.GetPlayerData() end
function B.IsLoggedIn() return ESX.IsPlayerLoaded() end
function B.GetJob() return normJob(ESX.GetPlayerData().job) end

function B.OnPlayerLoaded(cb) RegisterNetEvent('esx:playerLoaded', function() cb() end) end
function B.OnPlayerUnload(cb) RegisterNetEvent('esx:onPlayerLogout', cb) end
function B.OnJobUpdate(cb) RegisterNetEvent('esx:setJob', function(job) cb(normJob(job)) end) end

return B
