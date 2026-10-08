fx_version 'cerulean'
game 'gta5'

name '{{RESOURCE_NAME}}'
author '{{AUTHOR}}'
description '{{DESCRIPTION}}'
version '1.0.0'

client_scripts {
    'client/main.lua',
    'client/nui.lua', -- @nui
}

server_script 'server/main.lua'

ui_page 'web/dist/index.html' -- @nui
nui_callback_strict_mode 'true' -- @nui
files { 'web/dist/**/*' } -- @nui
