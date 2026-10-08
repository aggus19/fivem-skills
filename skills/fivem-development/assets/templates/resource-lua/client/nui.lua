-- NUI bridge for web/. Build with `bun run --bun build` or `npm run build`.
local RESOURCE = GetCurrentResourceName()
local isOpen = false
local ready = false
local openData

local function setOpen(open, data)
    isOpen = open
    openData = open and data or nil
    if open and not ready then return end -- no focus until the page has registered listeners
    SendNUIMessage({ action = open and 'open' or 'close', data = data })
    SetNuiFocus(open, open)
end

RegisterCommand(RESOURCE .. '_ui', function()
    setOpen(not isOpen, { title = RESOURCE }) -- also permits closing after a UI failure
end, false)

RegisterNUICallback('ready', function(_, cb)
    ready = true
    cb({ ok = true })
    setOpen(isOpen, openData) -- resynchronize after an early open or a page reload
end)

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
    if resource == RESOURCE then SetNuiFocus(false, false) end
end)
