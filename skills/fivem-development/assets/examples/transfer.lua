-- Illustrative transaction body for custom InnoDB accounts, not framework balances.
-- Caller authenticates/authorizes the accounts and claims a durable operation ID.
-- This function never retries: an unclassified failure can mean an ambiguous commit.
return function(startTransaction, fromCid, toCid, amount)
    if type(fromCid) ~= 'string' or type(toCid) ~= 'string' or fromCid == toCid
        or #fromCid == 0 or #toCid == 0 or #fromCid > 64 or #toCid > 64
        or type(amount) ~= 'number' or amount ~= amount or amount <= 0
        or amount > 1000000000 or amount % 1 ~= 0 then
        return false, 'invalid'
    end
    local a, b = fromCid, toCid
    if b < a then a, b = b, a end
    local denied
    local called, committed = pcall(startTransaction, function(query)
        -- Separate exact-key reads make lock order explicit; citizenid must be UNIQUE.
        local first = query('SELECT citizenid FROM bank_accounts WHERE citizenid = ? FOR UPDATE', { a })
        local second = query('SELECT citizenid FROM bank_accounts WHERE citizenid = ? FOR UPDATE', { b })
        if #first ~= 1 or #second ~= 1 then
            denied = 'missing_account'
            return false
        end
        local debit = query('UPDATE bank_accounts SET balance = balance - ? WHERE citizenid = ? AND balance >= ?',
            { amount, fromCid, amount })
        if debit.affectedRows ~= 1 then
            denied = 'insufficient_funds'
            return false
        end
        local credit = query('UPDATE bank_accounts SET balance = balance + ? WHERE citizenid = ? AND balance <= ?',
            { amount, toCid, 9007199254740991 - amount })
        if credit.affectedRows ~= 1 then
            denied = 'credit_rejected'
            return false
        end
        -- A real service writes its durable operation result + ledger INSIDE this transaction.
        return true
    end)
    if called and committed == true then return true end
    -- Even rollback may fail; the adapter does not classify SQL/connection/commit errors.
    return false, denied or 'unconfirmed'
end
