-- Fixture: the client reports its own delivery distance (the server must compute it).
local distance = #(GetEntityCoords(PlayerPedId()) - vec3(0.0, 0.0, 0.0))
local ok = lib.callback.await('eco:job:payment', false, { distance_delivery = distance })
