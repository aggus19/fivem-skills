local B = {}

function B.GetPlayerData() return {} end
function B.IsLoggedIn() return NetworkIsPlayerActive(PlayerId()) end
function B.GetJob() return nil end

function B.OnPlayerLoaded(cb)
    AddEventHandler('playerSpawned', function() cb() end) -- fired by spawnmanager
end
function B.OnPlayerUnload() end
function B.OnJobUpdate() end

return B
