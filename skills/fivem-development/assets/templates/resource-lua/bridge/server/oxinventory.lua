-- Shared ox_inventory item helpers (used by every server bridge when ox_inventory is running).
local ox = exports.ox_inventory
local M = {}

function M.AddItem(src, item, count, metadata)
    if not ox:CanCarryItem(src, item, count, metadata) then return false end
    local success = ox:AddItem(src, item, count, metadata)
    return success == true
end

function M.RemoveItem(src, item, count, metadata)
    if (ox:GetItemCount(src, item, metadata) or 0) < count then return false end
    return ox:RemoveItem(src, item, count, metadata) == true
end

function M.HasItem(src, item, count)
    return (ox:GetItemCount(src, item) or 0) >= (count or 1)
end

function M.CanCarry(src, item, count)
    return ox:CanCarryItem(src, item, count) == true
end

return M
