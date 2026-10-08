-- Server-only config: never listed in shared/client scripts or `files`.
ServerConfig = {}

-- Authoritative prices. The client never sends a price.
ServerConfig.Prices = {
    water = 5,
    bread = 8,
}

ServerConfig.MaxPerPurchase = 20
ServerConfig.PurchaseCooldown = 2      -- seconds
ServerConfig.MaxDistance = 5.0         -- metres between player and shop
ServerConfig.Account = 'cash'          -- 'cash' | 'bank'

-- Secrets come from convars set in server.cfg with `set` (server-only), e.g.:
-- set {{RESOURCE_NAME}}:webhook "https://discord.com/api/webhooks/..."
ServerConfig.Webhook = GetConvar('{{RESOURCE_NAME}}:webhook', '')
