-- Custom, non-economic progress only. Memory survives failed writes, not process crashes.
-- write(key, payload) may yield; return exactly true only after the DB acknowledges it.
-- payload is an immutable serialized snapshot. Single resource owns each key.
return function(write, maxEntries)
    assert(type(write) == 'function')
    maxEntries = maxEntries or 4096
    local entries, size = {}, 0
    local store = {}

    local function evict(key, entry)
        if entry.released and not entry.writing and entry.saved == entry.version then
            entries[key] = nil
            size = size - 1
            return true
        end
        return false
    end

    function store.put(key, payload)
        assert(type(key) == 'string' and type(payload) == 'string')
        local entry = entries[key]
        if not entry then
            if size >= maxEntries then return false, 'queue_full' end
            entry = { version = 0, saved = 0 }
            entries[key], size = entry, size + 1
        end
        entry.payload = payload
        entry.version = entry.version + 1
        entry.released = false
        return true
    end

    function store.flush(key)
        local entry = entries[key]
        if not entry then return true end
        if entry.writing then return false, 'busy' end
        if entry.saved == entry.version then return true end
        local version, payload = entry.version, entry.payload
        entry.writing = true
        local called, acknowledged = pcall(write, key, payload)
        entry.writing = false
        if called and acknowledged == true then entry.saved = version end
        evict(key, entry)
        if not called or acknowledged ~= true then return false, 'write_failed' end
        if entry.saved ~= entry.version then return false, 'newer_changes_pending' end
        return true
    end

    function store.flushAll()
        local keys = {}
        for key in pairs(entries) do keys[#keys + 1] = key end
        local clean = true
        for _, key in ipairs(keys) do
            if not store.flush(key) then clean = false end
        end
        return clean
    end

    function store.release(key)
        local entry = entries[key]
        if not entry then return true end
        entry.released = true
        return evict(key, entry) -- failed/in-flight writes remain available for retry
    end

    function store.pending(key)
        local entry = entries[key]
        return entry ~= nil and (entry.writing or entry.saved ~= entry.version) or false
    end

    return store
end
