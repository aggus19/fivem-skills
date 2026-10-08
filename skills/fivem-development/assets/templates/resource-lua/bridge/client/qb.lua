local QBCore = exports['qb-core']:GetCoreObject()
local B = {}

local function normJob(j)
    return j and { name = j.name, grade = j.grade.level, label = j.label, onDuty = j.onduty } or nil
end

function B.GetPlayerData() return QBCore.Functions.GetPlayerData() end

function B.IsLoggedIn()
    if LocalPlayer.state.isLoggedIn ~= nil then return LocalPlayer.state.isLoggedIn end
    return B.GetPlayerData().citizenid ~= nil
end

function B.GetJob() return normJob(B.GetPlayerData().job) end

function B.OnPlayerLoaded(cb) RegisterNetEvent('QBCore:Client:OnPlayerLoaded', cb) end
function B.OnPlayerUnload(cb) RegisterNetEvent('QBCore:Client:OnPlayerUnload', cb) end
function B.OnJobUpdate(cb) RegisterNetEvent('QBCore:Client:OnJobUpdate', function(job) cb(normJob(job)) end) end

return B
