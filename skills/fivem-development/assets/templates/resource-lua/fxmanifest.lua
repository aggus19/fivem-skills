fx_version 'cerulean'
game 'gta5'
lua54 'yes' -- optional since Lua 5.3 was removed from FXServer (2025-06); harmless

name '{{RESOURCE_NAME}}'
author '{{AUTHOR}}'
description '{{DESCRIPTION}}'
version '1.0.0'

ox_lib 'locale'

shared_scripts {
    '@ox_lib/init.lua',
    'config/shared.lua',
    'bridge/init.lua',
}

client_scripts {
    'client/main.lua',
    'client/nui.lua', -- @nui
}

server_scripts {
    '@oxmysql/lib/MySQL.lua',
    'config/server.lua',
    'server/main.lua',
}

ui_page 'web/dist/index.html' -- @nui
nui_callback_strict_mode 'true' -- @nui

files {
    'locales/*.json',
    'bridge/client/*.lua',
    'web/dist/**/*', -- @nui
}

dependencies {
    '/server:12913',
    '/onesync',
    'ox_lib',
    'oxmysql',
}
