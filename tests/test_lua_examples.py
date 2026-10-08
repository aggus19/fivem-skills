"""Lua 5.4 logic tests with fault injection, not FXServer/MySQL integration tests.

Optional test-only dependency: lupa==2.8 (import its lua54 runtime explicitly).
Set FIVEM_REQUIRE_LUA_TESTS=1 in CI to disallow skipped Lua checks.
The installed skill's scripts remain standard-library Python.
"""
import os
import unittest
from pathlib import Path

try:
    from lupa.lua54 import LuaRuntime
except ImportError:
    if os.environ.get('FIVEM_REQUIRE_LUA_TESTS') == '1':
        raise
    LuaRuntime = None

EXAMPLES = Path(__file__).resolve().parents[1] / 'skills/fivem-development/assets/examples'


@unittest.skipIf(LuaRuntime is None, 'install test-only lupa==2.8 to execute Lua 5.4 fault tests')
class WriteQueueTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().newStore = self.lua.execute((EXAMPLES / 'versioned_store.lua').read_text(encoding='utf-8'))

    def test_failed_write_and_unload_retain_snapshot_for_retry(self):
        self.lua.execute('''
            local fail, durable = true, {}
            local store = newStore(function(key, payload)
                if fail then error('DB unavailable') end
                durable[key] = payload
                return true
            end)
            assert(store.put('character', 'first'))
            assert(not store.flush('character'))
            assert(not store.release('character'))
            assert(store.pending('character'))
            fail = false
            assert(store.flushAll())
            assert(durable.character == 'first')
            assert(not store.pending('character'))
        ''')

    def test_write_during_await_is_not_acknowledged_by_old_snapshot(self):
        self.lua.execute('''
            local durable, writes = {}, 0
            local store = newStore(function(key, payload)
                writes = writes + 1
                coroutine.yield()
                durable[key] = payload
                return true
            end)
            store.put('character', 'old')
            local first = coroutine.create(function() store.flush('character') end)
            assert(coroutine.resume(first))
            store.put('character', 'new')
            assert(not store.flush('character')) -- no overlapping writer
            assert(writes == 1)
            assert(coroutine.resume(first))
            assert(durable.character == 'old' and store.pending('character'))
            local second = coroutine.create(function() assert(store.flush('character')) end)
            assert(coroutine.resume(second))
            assert(coroutine.resume(second))
            assert(durable.character == 'new' and not store.pending('character'))
        ''')

    def test_release_during_write_then_new_session_does_not_evict_new_state(self):
        self.lua.execute('''
            local store = newStore(function() coroutine.yield(); return true end, 1)
            store.put('character', 'old')
            local co = coroutine.create(function() store.flush('character') end)
            assert(coroutine.resume(co))
            assert(not store.release('character'))
            store.put('character', 'new')
            assert(coroutine.resume(co))
            assert(store.pending('character'))
            assert(not store.put('other', 'payload')) -- retained entry still occupies queue
        ''')

    def test_false_and_nil_are_not_success_acknowledgements(self):
        self.lua.execute('''
            for _, writer in ipairs({function() return false end, function() end}) do
                local store = newStore(writer)
                store.put('key', 'value')
                assert(not store.flush('key'))
                assert(store.pending('key'))
            end
        ''')

    def test_bounded_queue_never_drops_pending_entry(self):
        self.lua.execute('''
            local saved = {}
            local store = newStore(function(k, v) saved[k] = v; return true end, 1)
            assert(store.put('first', 'v1'))
            assert(not store.put('second', 'v2'))
            assert(store.put('first', 'v3'))
            assert(store.flushAll())
            assert(saved.first == 'v3' and saved.second == nil)
            assert(store.release('first'))
            assert(store.put('second', 'v2'))
        ''')


@unittest.skipIf(LuaRuntime is None, 'install test-only lupa==2.8 to execute Lua 5.4 fault tests')
class TransferTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().transfer = self.lua.execute((EXAMPLES / 'transfer.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
            accounts = {alice = 100, bob = 0}
            calls, locks = 0, {}
            function transaction(body)
                calls = calls + 1
                local before = {}; for k,v in pairs(accounts) do before[k] = v end
                local ok, commit = pcall(body, function(sql, params)
                    if sql:find('SELECT', 1, true) then
                        local key = params[1]; locks[#locks+1] = key
                        return accounts[key] and {{citizenid=key}} or {}
                    end
                    local amount, key = params[1], params[2]
                    if sql:find('balance -', 1, true) then
                        if not accounts[key] or accounts[key] < amount then return {affectedRows=0} end
                        accounts[key] = accounts[key] - amount
                    else
                        if throwCredit then error('credit failure') end
                        if rejectCredit or not accounts[key] or accounts[key] > params[3] then return {affectedRows=0} end
                        accounts[key] = accounts[key] + amount
                    end
                    return {affectedRows=1}
                end)
                if not ok or commit == false then accounts=before; return false end
                return true
            end
        ''')

    def test_missing_receiver_never_debits_sender(self):
        self.lua.execute("accounts.bob=nil; assert(not transfer(transaction,'alice','bob',10)); assert(accounts.alice==100)")

    def test_rejected_credit_rolls_back_debit(self):
        self.lua.execute("rejectCredit=true; assert(not transfer(transaction,'alice','bob',10)); assert(accounts.alice==100 and accounts.bob==0)")

    def test_sql_error_does_not_trigger_blind_retry(self):
        self.lua.execute("throwCredit=true; assert(not transfer(transaction,'alice','bob',10)); assert(calls==1 and accounts.alice==100)")

    def test_insufficient_funds_do_not_credit_receiver(self):
        self.lua.execute("assert(not transfer(transaction,'alice','bob',101)); assert(accounts.alice==100 and accounts.bob==0)")

    def test_valid_transfer_conserves_balance_and_sorts_locks(self):
        self.lua.execute("accounts.bob=100; assert(transfer(transaction,'bob','alice',10)); assert(accounts.alice==110 and accounts.bob==90); assert(locks[1]=='alice' and locks[2]=='bob')")

    def test_invalid_amounts_and_self_transfer_never_reach_database(self):
        self.lua.execute('''
            for _, amount in ipairs({0, -1, 0/0, math.huge, 1.5, 1000000001, '10'}) do
                assert(not transfer(transaction, 'alice', 'bob', amount))
            end
            assert(not transfer(transaction, 'alice', 'alice', 10))
            assert(calls == 0)
        ''')


@unittest.skipIf(LuaRuntime is None, 'install test-only lupa==2.8 to execute Lua 5.4 fault tests')
class PurchaseTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        source = EXAMPLES.parent / 'templates/resource-lua/server/purchase.lua'
        self.lua.globals().purchase = self.lua.execute(source.read_text(encoding='utf-8'))
        self.lua.execute("""
            debits, grants, refunds, recoveries = 0, 0, 0, 0
            current = true
            ops = {
                isCurrent = function() return current end,
                debit = function() debits=debits+1; return true end,
                grant = function() grants=grants+1; return true end,
                refund = function() refunds=refunds+1; return true end,
                recovery = function(stage) recoveries=recoveries+1; recoveryStage=stage end,
            }
        """)

    def test_success_does_not_refund(self):
        self.lua.execute('assert(purchase(ops)); assert(debits==1 and grants==1 and refunds==0 and recoveries==0)')

    def test_denied_debit_never_grants(self):
        self.lua.execute('ops.debit=function() return false end; assert(not purchase(ops)); assert(grants==0 and refunds==0)')

    def test_known_grant_failure_refunds_once(self):
        self.lua.execute('ops.grant=function() return false end; assert(not purchase(ops)); assert(refunds==1 and recoveries==0)')

    def test_ambiguous_grant_never_blindly_refunds(self):
        self.lua.execute("ops.grant=function() error('unknown') end; assert(not purchase(ops)); assert(refunds==0 and recoveryStage=='grant_unknown')")

    def test_failed_refund_requires_recovery(self):
        self.lua.execute("ops.grant=function() return false end; ops.refund=function() return false end; assert(not purchase(ops)); assert(recoveryStage=='refund_rejected')")

    def test_unknown_debit_does_not_grant_or_refund(self):
        self.lua.execute("ops.debit=function() end; assert(not purchase(ops)); assert(grants==0 and refunds==0 and recoveryStage=='debit_unknown')")

    def test_session_change_while_debit_yields_never_grants_to_new_session(self):
        self.lua.execute("""
            ops.debit=function() coroutine.yield(); return true end
            local co=coroutine.create(function() assert(not purchase(ops)) end)
            assert(coroutine.resume(co)); current=false; assert(coroutine.resume(co))
            assert(grants==0 and refunds==0 and recoveryStage=='debited_session_changed')
        """)


@unittest.skipIf(LuaRuntime is None, 'install test-only lupa==2.8 to execute Lua 5.4 fault tests')
class NuiBridgeTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            callbacks, events, commands, messages = {}, {}, {}, {}
            focus=false
            function GetCurrentResourceName() return 'demo' end
            function RegisterNUICallback(name, fn) callbacks[name]=fn end
            function RegisterCommand(name, fn) commands[name]=fn end
            function AddEventHandler(name, fn) events[name]=fn end
            function SendNUIMessage(data) messages[#messages+1]=data end
            function SetNuiFocus(value) focus=value end
            function reply(data) assert(data.ok) end
        """)
        source=EXAMPLES.parent / 'templates/resource-lua/client/nui.lua'
        self.lua.execute(source.read_text(encoding='utf-8'))

    def test_early_open_waits_for_listener_handshake(self):
        self.lua.execute("""
            commands.demo_ui()
            assert(not focus and #messages==0)
            callbacks.ready({},reply)
            assert(focus and messages[1].action=='open')
        """)

    def test_close_before_ready_does_not_reopen_later(self):
        self.lua.execute("""
            commands.demo_ui(); callbacks.close({},reply); callbacks.ready({},reply)
            assert(not focus and messages[#messages].action=='close')
        """)

    def test_reload_resync_and_resource_stop_release_focus(self):
        self.lua.execute("""
            callbacks.ready({},reply); commands.demo_ui(); callbacks.ready({},reply)
            assert(focus and messages[#messages].action=='open')
            events.onResourceStop('demo'); assert(not focus)
        """)


@unittest.skipIf(LuaRuntime is None, 'install test-only lupa==2.8 to execute Lua 5.4 fault tests')
class ShopHandlerTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        template = EXAMPLES.parent / 'templates/resource-lua'
        self.lua.globals().purchaseFlow = self.lua.execute((template / 'server/purchase.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
            callbacks, events = {}, {}
            debits, grants, refunds, recoveries = 0, 0, 0, 0
            function GetCurrentResourceName() return 'demo' end
            function GetConvar(_, default) return default end
            function GetPlayerName() return 'name' end
            function GetPlayerPed() return 1 end
            function GetPlayerRoutingBucket() return 0 end
            function DoesEntityExist() return true end
            function GetEntityCoords()
                return setmetatable({}, {__sub=function()
                    return setmetatable({}, {__len=function() return 0 end})
                end})
            end
            function AddEventHandler(name, fn) events[name]=fn end
            function require() return purchaseFlow end
            lib={callback={register=function(name, fn) callbacks[name]=fn end},
                 print={info=function() end, error=function() end},
                 table={contains=function(list,item) return item=='water' end}}
            Config={Shops={market={coords={},items={'water'}}}}
            Bridge={
                GetPlayer=function() return {} end,
                GetIdentifier=function() return 'character' end,
                CanCarry=function() return true end,
                RemoveMoney=function() debits=debits+1; return true end,
                AddItem=function() grants=grants+1; return true end,
                AddMoney=function() refunds=refunds+1; return true end,
            }
        ''')
        self.lua.execute((template / 'config/server.lua').read_text(encoding='utf-8'))
        self.lua.execute((template / 'server/main.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
            buy=callbacks['demo:server:buy']
            ServerConfig.PurchaseCooldown=0
            ServerConfig.RecordRecovery=function(record) recoveries=recoveries+1 end
        ''')

    def test_default_scaffold_does_not_mutate_economy(self):
        self.lua.execute("local ok,reason=buy(1,'market','water',1); assert(not ok and reason=='unavailable'); assert(debits==0 and grants==0)")

    def test_enabled_integrated_flow_releases_lock_after_success(self):
        self.lua.execute("ServerConfig.PurchasesEnabled=true; assert(buy(1,'market','water',1)); assert(buy(1,'market','water',1)); assert(debits==2 and grants==2)")

    def test_invalid_quantities_never_reach_mutation(self):
        self.lua.execute('''
            ServerConfig.PurchasesEnabled=true
            for _,count in ipairs({0,-1,1.5,0/0,math.huge,21,'2'}) do
                assert(not buy(1,'market','water',count))
            end
            assert(debits==0 and grants==0)
        ''')

    def test_concurrent_request_is_blocked_while_debit_yields(self):
        self.lua.execute('''
            ServerConfig.PurchasesEnabled=true
            Bridge.RemoveMoney=function() debits=debits+1; coroutine.yield(); return true end
            local co=coroutine.create(function() assert(buy(1,'market','water',1)) end)
            assert(coroutine.resume(co))
            local ok,reason=buy(1,'market','water',1)
            assert(not ok and reason=='busy' and debits==1)
            assert(coroutine.resume(co)); assert(grants==1)
        ''')

    def test_missing_actor_unknown_item_and_oversized_names_do_not_mutate(self):
        self.lua.execute('''
            ServerConfig.PurchasesEnabled=true
            assert(not buy(1,'market','unlisted',1))
            assert(not buy(1,string.rep('a',65),'water',1))
            assert(not buy(1,'market',string.rep('b',65),1))
            Bridge.GetPlayer=function() return nil end
            assert(not buy(1,'market','water',1))
            assert(debits==0 and grants==0 and refunds==0)
        ''')

    def test_wrong_bucket_missing_ped_and_distance_do_not_mutate(self):
        self.lua.execute('''
            ServerConfig.PurchasesEnabled=true
            GetPlayerRoutingBucket=function() return 99 end
            assert(not buy(1,'market','water',1))
            GetPlayerRoutingBucket=function() return 0 end
            DoesEntityExist=function() return false end
            assert(not buy(1,'market','water',1))
            DoesEntityExist=function() return true end
            GetEntityCoords=function()
                return setmetatable({}, {__sub=function()
                    return setmetatable({}, {__len=function() return 500 end})
                end})
            end
            assert(not buy(1,'market','water',1))
            assert(debits==0 and grants==0 and refunds==0)
        ''')

    def test_invalid_config_price_cannot_wrap_or_create_free_grant(self):
        self.lua.execute('''
            ServerConfig.PurchasesEnabled=true
            for _,price in ipairs({0,-1,1.5,0/0,math.huge,math.maxinteger,'5'}) do
                ServerConfig.Prices.water=price
                assert(not buy(1,'market','water',2))
            end
            assert(debits==0 and grants==0 and refunds==0)
        ''')

    def test_character_change_during_capacity_check_prevents_debit(self):
        self.lua.execute('''
            ServerConfig.PurchasesEnabled=true
            Bridge.CanCarry=function() coroutine.yield(); return true end
            local co=coroutine.create(function() assert(not buy(1,'market','water',1)) end)
            assert(coroutine.resume(co))
            Bridge.GetIdentifier=function() return 'different_character' end
            assert(coroutine.resume(co))
            assert(debits==0 and grants==0 and refunds==0)
        ''')

    def test_disconnect_during_mutation_leaves_character_for_reconciliation(self):
        self.lua.execute('''
            ServerConfig.PurchasesEnabled=true
            Bridge.RemoveMoney=function() debits=debits+1; coroutine.yield(); return true end
            local co=coroutine.create(function() assert(not buy(1,'market','water',1)) end)
            assert(coroutine.resume(co)); source=1; events.playerDropped()
            assert(coroutine.resume(co)); assert(grants==0 and refunds==0 and recoveries==1)
            local ok,reason=buy(2,'market','water',1)
            assert(not ok and reason=='busy')
        ''')


if __name__ == '__main__':
    unittest.main()
