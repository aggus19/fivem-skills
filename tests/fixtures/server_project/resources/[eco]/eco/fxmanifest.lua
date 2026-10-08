fx_version 'cerulean'
game 'gta5'

name 'eco'
author 'fixture'
description 'Fixture: economy endpoints with known exploit classes'
version '1.0.0'

server_scripts {
    'server/*.lua',
}

client_script 'client/main.lua'

files {
    'stream/[props]/*.ytyp',
}

data_file 'DLC_ITYP_REQUEST' 'stream/[props]/present.ytyp'
data_file 'DLC_ITYP_REQUEST' 'stream/[props]/missing.ytyp'
