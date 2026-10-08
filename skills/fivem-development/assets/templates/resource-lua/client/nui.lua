-- NUI bridge for web/ (React + Vite template). Build the UI with `npm run build` inside web/.
local RESOURCE = GetCurrentResourceName()
local isOpen = false

local function setOpen(open, data)
    isOpen = open
    SendNUIMessage({ action = open and 'open' or 'close', data = data })
    SetNuiFocus(open, open)
end

RegisterCommand(RESOURCE .. '_ui', function()
    setOpen(true, { title = RESOURCE })
end, false)

RegisterNUICallback('close', function(_, cb)
    setOpen(false)
    cb({ ok = true }) -- always answer, or the browser fetch hangs
end)

RegisterNUICallback('action', function(data, cb)
    -- Browser data is client-controlled: forward only the intent and let the server validate.
    local kind = type(data) == 'table' and data.kind or nil
    cb({ ok = type(kind) == 'string' })
end)

AddEventHandler('onResourceStop', function(resource)
    if resource == RESOURCE and isOpen then SetNuiFocus(false, false) end
end)
