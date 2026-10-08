# Licensing, monetisation and platform policy

Baseline: Creator Platform License Agreement (PLA) "Last Updated: Sept. 10 2026" (read in full from the official PDF), Cfx docs for Tebex and Asset Escrow — verified 2026-10-07. Not legal advice: quote the section, link the official text, and tell the user to read it.

## Contents
1. Documents that apply
2. PLA structure (section map)
3. Licence, branding and content rules (§2)
4. Commercial exploitation: prohibited methods (§3.1)
5. Server Admin responsibility and third parties (§4–§5)
6. Cfx Marketplace (§6)
7. Tebex (authorized monetisation partner)
8. Asset Escrow
9. Rockstar Mod Guidelines and community rules
10. Open-source licences of common resources
11. Feature request → policy decision table
12. Practical rules for generated code
13. Sources

## 1. Documents that apply
- **Creator Platform License Agreement** (https://fivem.net/terms → redirects to the PDF dated 2026-09-10). Binding agreement with Rockstar Games, Inc. / Take-Two; it incorporates the **Rockstar Terms of Service** and **Community Guidelines** by reference and is conditioned on "Creator Policies", including the **Rockstar Games Mod Guidelines** (§1.3).
- Cfx docs: Tebex store setup, Asset Escrow.
- Tebex Acceptable Use Policy and Terms (referenced by the Cfx Tebex docs).
- History: Cfx.re joined Rockstar Games in 2023; earlier PLA revision effective 2026-01-12 (Marketplace launch); current revision 2026-09-10.

## 2. PLA structure (section map)
| § | Topic |
|---|---|
| 1.1–1.6 | Definitions: Creator Services (FiveM, RedM), Covered Games, Creator Policies, Operator Services / Custom Server / Server Admin, Player Services, Creator Content |
| 2.1–2.5 | Limited, revocable licence; restrictions; no sponsorship/endorsement + mandatory disclaimer; music and voiceover limits; reservation of rights |
| 3.1–3.2 | Prohibited commercial methods (8 items); you are responsible for legal compliance (consumer, tax, privacy) |
| 4 | Server Admins are responsible for all Server Content and legal compliance incl. personal data |
| 5.1–5.3 | Third-party content at own risk; **Authorized Services** may be required, Unauthorized Service Providers may be prohibited (changes effective 30 days after posting) |
| 6.1–6.4 | Marketplace: agency, licence grant to buyers, restrictions (no resale, no reverse engineering, no generative-AI use) |
| 7.1–7.4 | Availability; Adverse Action for violations; no refunds liability |
| 8 | Rockstar does not resolve disputes between users, admins and creators |

## 3. Licence, branding and content rules (§2)
- **§2.2** No use that violates third-party rights or law, and no use of Covered Games elements as a brand/logo/source identifier in commerce.
- **§2.3** Don't imply Rockstar approval; no Rockstar logos/trademarks/IP in the **server name or branding**. All websites, product listings, storefronts and other user-facing info for a Custom Server must (1) clearly identify the operator with a **valid contact email**, and (2) show a disclaimer substantially like: **"[CUSTOM SERVER NAME] IS NOT APPROVED, SPONSORED, OR ENDORSED BY ROCKSTAR GAMES."**
- **§2.4** No third-party licensed music (ASCAP/BMI/SESAC-type works) created, uploaded or distributed via the Creator Services — includes in-game GTA soundtrack reuse; no modification of Covered-Game voice recordings/voiceover performances. Impacts radio/boombox/"play YouTube/Spotify URL" resources.
- **§2.5** Rockstar owns the Covered Games and derivative works, except separate IP you hold in your own creations.

## 4. Commercial exploitation: prohibited methods (§3.1)
You may not commercially exploit the licence, Creator Content or Custom Server through:
1. **Cash Out**: any mechanic where users pay Real Money (fiat, assets, crypto) in and receive Real Money or equivalent value out — **including Real Money gambling of any kind** (slots, blackjack, poker, casino games).
2. **Loot boxes, gacha, random drawings, sweepstakes** or functionally similar chance-based mechanics **offered or sold for Real Money or for in-game virtual currency**.
3. Selling **in-game virtual currency for Real Money**.
4. Offering, selling or facilitating access to **Virtual Items created by Rockstar**.
5. Operating a server **by, for, or in ongoing commercial association with a third-party brand** ("official" brand/sponsor servers).
6. Operating a website/storefront/marketplace that **aggregates third-party Server Content and sells/licenses it** to Server Admins.
7. Creator Content with **third-party promotions, ads, endorsements or sponsorships** (in-game or as Marketplace Content).
8. Facilitating use, sale or promotion of **cryptocurrencies or crypto assets** (NFTs, tokens, meme coins).
The list is non-exhaustive and may change; Rockstar may suspend commercial exploitation at its discretion. **§3.2**: you alone are responsible for consumer-protection, advertising, e-commerce, tax, subscription and data-privacy law.

## 5. Server Admin responsibility and third parties (§4–§5)
- **§4** The Server Admin is responsible for all Server Content on their server (including content uploaded by others), for compliance with the Agreement and Creator Policies, and for applicable law **including personal-data processing and privacy** (logs, IPs, hardware tokens, screenshots).
- **§5.2** Rockstar may designate **Authorized Services** (e-commerce, payment, hosting, marketplaces, video platforms) and require their use, and may prohibit **Unauthorized Service Providers**; list changes take effect 30 days after posting on the Websites.
- **§7.2** Breaches can lead to Adverse Action against users, accounts, content and servers.

## 6. Cfx Marketplace (§6)
- Launched 2026-01-12 (curated storefront, phased creator onboarding via a support form).
- Rockstar and the Operator act as **agent** for Marketplace Creators; creators provide reasonable technical support; Rockstar/Operator handle payment and website support (§6.2).
- Buyer licence (§6.3): limited, non-exclusive, non-transferable, royalty-free, worldwide, perpetual — to incorporate into Custom Servers for which you hold a server key, distribute only as part of that server, commercially exploit as permitted, and modify only as needed. One-time purchases are irrevocable; subscriptions end when you cancel or the creator stops offering them.
- Restrictions (§6.4): no standalone resale/sharing/redistribution; **no disassembly, decompiling, reverse engineering or derivative works**; no modification beyond §6.3; **no use to develop, train, enhance, tune or provide source material for Generative AI tools**. → Never paste purchased Marketplace code into AI training sets; when a user shares Marketplace code for help, work only on what they are licensed to modify and do not attempt to decrypt escrowed parts.

## 7. Tebex (authorized monetisation partner)
- Cfx docs: "Tebex is our authorized monetization partner for the Cfx Platform" and "the exclusive monetization partner of FiveM"; **"The use of any other platform or payment provider is prohibited and is a violation of the Platform License Agreement."** (PayPal/Patreon/Ko-fi/crypto links for server perks = violation; calling a paid perk a "donation" does not change that.)
- Monetisation is also subject to the PLA and the Tebex AUP/Terms. Players may buy "virtual items and other game-related content" within §3.1 limits.
- Setup: Tebex panel → Connect Game Server → Plugin; `sv_tebexSecret yourkey` in `server.cfg` (keep it `set`-style/server-only, never in a resource or `setr`).
- Escrowed resources are sold through Tebex packages ("FiveM Asset" type).

## 8. Asset Escrow
- Upload a zip (max 1 GB) to the Cfx.re Portal; it is encrypted. Escrow-capable file types: **Lua, YFT, YDD, YDR**. **NUI is not supported.** Obfuscation is unnecessary for escrowed resources.
- `escrow_ignore { 'config.lua', 'stream/*.yft', 'stream/**/*.yft' }` keeps files readable (configs, locales, bridges).
- Unauthorized servers fail to start the resource ("You lack the required entitlement"). Subscription assets stop when the subscription lapses.
- Re-uploading replaces the current version (docs: the previous version is not kept; users who downloaded older versions keep them). Assets cannot be transferred between accounts.
- Escrow protects code, **not security**: client code still runs on the client and net events are still callable — audit your server side as usual.
- GTA V Enhanced: escrow not available yet at baseline (see gta5-enhanced.md).
- Never help bypass escrow, decrypt protected resources or redistribute leaks (PLA §6.4; leaks are also the main backdoor vector — audit-checklist.md).

## 9. Rockstar Mod Guidelines and community rules
The official page (https://www.rockstargames.com/community-resources/mod-guidelines, published 2026-09-10) did not render for automated reading; the points below come from press coverage — **UNVERIFIED against the primary text**:
- Don't combine maps/characters/assets/IP from one Rockstar title into another; don't extend official storylines/characters.
- Don't use third-party IP (art, music, brands, logos, real-world likenesses) or real people's voice/image without permission; don't modify Rockstar voiceover performances (matches PLA §2.4).
- No real-money gambling, loot boxes/gacha, virtual-currency sales, crypto/NFTs (matches PLA §3.1).
- Multiplayer modding is limited to Rockstar's licensed Creator Platform (FiveM/RedM) unless Rockstar says otherwise.
Also binding via the PLA preamble: Rockstar TOS and Community Guidelines (harassment, hate, cheating, illegal content).
## 10. Open-source licences of common resources
| Resource | Licence | Practical implication |
|---|---|---|
| ox_lib, oxmysql, ox_core | LGPL-3.0 | Use freely; modifications to the library itself stay LGPL |
| ox_inventory, ox_doorlock, ox_fuel | GPL-3.0 | Distributed modified versions stay GPL with source |
| ox_target, pma-voice, vRP | MIT | Permissive; keep notices |
| qbx_core, qb-core, es_extended, ND_Core, Fivemanage SDK | GPL-3.0 | Selling escrowed modified copies of GPL code violates the licence |
| screencapture | AGPL-3.0 | Network use counts as distribution |
- Resources that only **call** framework exports are generally treated as separate works; resources that **copy** GPL code must stay GPL (not legal advice).

## 11. Feature request → policy decision table
| Request | Verdict | Basis |
|---|---|---|
| Casino where players buy chips with real money / cash out | **No** | §3.1(1) |
| Slot machine / roulette using only in-game money earned in game | **Gray — flag** (no Real Money in/out, but chance mechanics "sold for in-game virtual currency" are listed in §3.1(2)); recommend no-wager or skill-based design | §3.1(2) |
| Paid "mystery crate", case opening, battle-pass random rewards | **No** (real or in-game currency) | §3.1(2) |
| Sell in-game money/coins for real money (Tebex or otherwise) | **No** | §3.1(3) |
| Sell custom-made cosmetics, custom vehicles, queue priority, VIP role via Tebex | Allowed within PLA/Tebex rules | Tebex docs; §3.1 |
| Sell access to stock (Rockstar-made) vehicles/items for real money | **Gray — flag** | §3.1(4) |
| PayPal/Patreon/crypto donations for perks | **No** | Tebex docs; §5.2; §3.1(8) |
| Sponsored server, in-game billboards for real brands | **No** | §3.1(5), §3.1(7) |
| Reselling other creators' scripts in your store | **No** | §3.1(6) |
| Radio/boombox playing commercial music | **No** for licensed music | §2.4 |
| Server named "Los Santos Official GTA RP" with Rockstar logo | **No** + add disclaimer and contact email | §2.3 |
| Train an AI on purchased Marketplace resources | **No** | §6.4(4) |

## 12. Practical rules for generated code
- Write original code; keep licence headers/attribution when adapting open source.
- No real-money gambling, chance-based paid mechanics, currency sales or crypto features; flag gray areas instead of silently building them.
- Monetisation hooks only through Tebex (e.g. server-side Tebex command/webhook handlers that grant perks after verifying the purchase server-side).
- Keep secrets server-side; minimise personal data (no IP/HWID logging without need; retention limits) — §4 makes the Server Admin responsible.
- Don't ship third-party IP (brands, logos, other games' assets, commercial music).

## 13. Sources
- Creator Platform License Agreement (2026-09-10): https://fivem.net/terms → https://static.cfx.re/platform-license-agreement-10-sept-2026.pdf
- Tebex store setup: https://docs.fivem.net/docs/server-manual/setting-up-a-tebex-store/
- Asset Escrow: https://docs.fivem.net/docs/server-manual/asset-escrow/
- Cfx Marketplace announcement (2026-01-12): https://forum.cfx.re/t/5369289
- Rockstar Mod Guidelines: https://www.rockstargames.com/community-resources/mod-guidelines · coverage: https://www.gamedeveloper.com/production/-do-not-rockstar-outlines-modding-rules-before-gta-vi-touches-down
- Licences: repository LICENSE files listed in versions.md
