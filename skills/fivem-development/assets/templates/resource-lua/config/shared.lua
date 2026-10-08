-- Shared config: sent to every client. Never put prices, rewards, webhooks or secrets here.
Config = {}

Config.Debug = false

-- Shop locations (coords are public information anyway)
Config.Shops = {
    downtown = {
        label = 'Downtown 24/7',
        coords = vec3(25.7, -1347.3, 29.5),
        blip = { sprite = 52, colour = 2, scale = 0.8 },
        items = { 'water', 'bread' }, -- item names only; prices live in config/server.lua
    },
}

Config.InteractDistance = 2.0
