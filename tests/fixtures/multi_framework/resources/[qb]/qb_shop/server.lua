local QBCore = exports['qb-core']:GetCoreObject()

QBCore.Functions.CreateCallback('qb_shop:buy', function(source, cb, item, amount)
    local Player = QBCore.Functions.GetPlayer(source)
    Player.Functions.RemoveMoney('cash', amount * 10)
    Player.Functions.AddItem(item, amount)
    cb(true)
end)

QBCore.Commands.Add('givecash', 'Give cash', {}, false, function(source, args)
    local Player = QBCore.Functions.GetPlayer(tonumber(args[1]))
    Player.Functions.AddMoney('cash', tonumber(args[2]))
end, 'admin')
