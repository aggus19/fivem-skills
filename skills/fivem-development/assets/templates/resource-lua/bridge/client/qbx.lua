local B = {}

local function normJob(j)
    return j and { name = j.name, grade = j.grade.level, label = j.label, onDuty = j.onduty } or nil
end

function B.GetPlayerData() return exports.qbx_core:GetPlayerData() end
function B.IsLoggedIn() return LocalPlayer.state.isLoggedIn == true end
function B.GetJob()
    local pd = B.GetPlayerData()
    return pd and normJob(pd.job)
end

-- QBCore:Client:OnPlayerLoaded is a local (non-networked) event in Qbox
function B.OnPlayerLoaded(cb) AddEventHandler('QBCore:Client:OnPlayerLoaded', cb) end
function B.OnPlayerUnload(cb) RegisterNetEvent('qbx_core:client:playerLoggedOut', cb) end
function B.OnJobUpdate(cb) RegisterNetEvent('QBCore:Client:OnJobUpdate', function(job) cb(normJob(job)) end) end

return B
