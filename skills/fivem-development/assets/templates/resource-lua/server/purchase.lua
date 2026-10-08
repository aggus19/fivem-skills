-- Compensating flow, NOT a cross-resource/database transaction.
-- Each adapter must return true=applied, false=not applied, throw/nil=unknown.
-- isCurrent must identify the original session; recovery must persist ambiguous cases.
-- No retry is performed here. The caller owns serialization and durable operation IDs.
return function(ops)
    local function call(name)
        local ok, result = pcall(ops[name])
        if not ok or type(result) ~= 'boolean' then return nil end
        return result
    end
    local function recover(stage)
        ops.recovery(stage)
        return false, 'recovery_required'
    end
    if not ops.isCurrent() then return false, 'invalid' end
    local debited = call('debit')
    if debited == nil then return recover('debit_unknown') end
    if not debited then return false, 'not_enough_money' end
    if not ops.isCurrent() then return recover('debited_session_changed') end
    local granted = call('grant')
    if granted == nil then return recover('grant_unknown') end
    if granted then return true, 'bought' end
    if not ops.isCurrent() then return recover('refund_session_changed') end
    local refunded = call('refund')
    if refunded ~= true then return recover(refunded == false and 'refund_rejected' or 'refund_unknown') end
    return false, 'cannot_carry'
end
