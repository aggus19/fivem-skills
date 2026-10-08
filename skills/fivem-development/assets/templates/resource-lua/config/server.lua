-- Server-only config: never listed in shared/client scripts or `files`.
ServerConfig = {}

-- This cross-framework shop is an integration example. Before enabling it, wire a
-- durable operation/recovery service, validate adapter return/yield contracts and
-- character-switch hooks, and pass the failure cases in the generated README.
ServerConfig.PurchasesEnabled = false
ServerConfig.RecordRecovery = function(operation)
    error('Implement durable purchase recovery before enabling the example shop')
end

-- Authoritative prices. The client never sends a price.
ServerConfig.Prices = {
    water = 5,
    bread = 8,
}

ServerConfig.MaxPerPurchase = 20
ServerConfig.MaxTransaction = 1000000
ServerConfig.PurchaseCooldown = 2      -- seconds
ServerConfig.MaxDistance = 5.0         -- metres between player and shop
ServerConfig.ShopBucket = 0           -- server-owned world policy; adapt for instanced shops
ServerConfig.Account = 'cash'          -- 'cash' | 'bank'

-- Secrets come from convars set in server.cfg with `set` (server-only), e.g.:
-- set {{RESOURCE_NAME}}:webhook "https://discord.com/api/webhooks/..."
ServerConfig.Webhook = GetConvar('{{RESOURCE_NAME}}:webhook', '')
