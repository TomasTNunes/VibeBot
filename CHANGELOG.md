# CHANGELOG


## v1.3.0 (2025-03-10)

### Bug Fixes

- Allow all available emoji buttons
  ([`2d3068c`](https://github.com/TomasTNunes/VibeBot/commit/2d3068cf1eaf4702ef1412e63db0727e43565c71))

- Handle CommandNotFound errors gracefully
  ([`0b65a50`](https://github.com/TomasTNunes/VibeBot/commit/0b65a504b394b26afc1295556335b615e8e0eb7d))

- Show queue time beyond next 15 tracks
  ([`824e003`](https://github.com/TomasTNunes/VibeBot/commit/824e003aaf7113048c2eca422899c2fab6304f64))

### Code Style

- Change /pl-show layout
  ([`cd7d8d5`](https://github.com/TomasTNunes/VibeBot/commit/cd7d8d5c3cde08da55f382ab54550673626aa0d2))

### Features

- Add / invite button
  ([`1eb6fed`](https://github.com/TomasTNunes/VibeBot/commit/1eb6fed55565bbdea4d279b1b0d8e80f479682b2))

- Add auto-disconnect / command
  ([`e6fe783`](https://github.com/TomasTNunes/VibeBot/commit/e6fe7833b6a209cef5749e61b452d1956a133f39))

- Add jump to track in queue / command
  ([`51144be`](https://github.com/TomasTNunes/VibeBot/commit/51144be174b508a9a283db5f442f73f505f3e2dc))

- Add move track in queue / command
  ([`61704d3`](https://github.com/TomasTNunes/VibeBot/commit/61704d3935c061027cab438ce707bd685212c29c))

- Add ping / command
  ([`ac8790e`](https://github.com/TomasTNunes/VibeBot/commit/ac8790ed34188c46bcd1124f9a26973f636a3ced))

- Add remove track from queue / command
  ([`fab1e46`](https://github.com/TomasTNunes/VibeBot/commit/fab1e4658b00e1db32cd5b3eaeef72284c2e0e5e))

- Add seek track time / command
  ([`ff00717`](https://github.com/TomasTNunes/VibeBot/commit/ff0071717df2874a4a8d807e997d812f03212669))

- Add setup-fix / command
  ([`ee5b5f8`](https://github.com/TomasTNunes/VibeBot/commit/ee5b5f8860dfe03365f209f52d19a06260f1569b))

- Add shuffle option for playlists
  ([`e228515`](https://github.com/TomasTNunes/VibeBot/commit/e228515db7b36462dc4d7917068888b5989f33a3))

- Clear queue / command
  ([`f3338d0`](https://github.com/TomasTNunes/VibeBot/commit/f3338d04073b03caa11ee3202586749e338b4bff))

- Fast forward and rewind / commands
  ([`66f9ac8`](https://github.com/TomasTNunes/VibeBot/commit/66f9ac83937ccbe8d0db0b7a78f4acc4187dcb89))

### Refactoring

- Add comment on MusicPlayerView for toDO
  ([`ec6e5ca`](https://github.com/TomasTNunes/VibeBot/commit/ec6e5ca862a50dc79a4b7aa0bbe1b9b8f83c5788))

- Fix typo in comment
  ([`63c49c0`](https://github.com/TomasTNunes/VibeBot/commit/63c49c0dc8a4428c3b4c81bfcb3f070b17d87651))

- Put bot invite link as environment variable
  ([`58b825d`](https://github.com/TomasTNunes/VibeBot/commit/58b825da516e686ca3fcd9960b4a37eac7439b20))


## v1.2.1 (2025-03-06)

### Bug Fixes

- Fix docker entrypoint
  ([`8745690`](https://github.com/TomasTNunes/VibeBot/commit/87456907db406909fc58b46ed8598bbfe761fe16))


## v1.2.0 (2025-03-06)

### Bug Fixes

- Docker compose lavalink network set external
  ([`108a8f6`](https://github.com/TomasTNunes/VibeBot/commit/108a8f669a187d8d072dccfa021afd81562f9eb6))

### Features

- Add arm64 support for docker
  ([`2895e44`](https://github.com/TomasTNunes/VibeBot/commit/2895e44cae8896a049463d1b10339d94c6897e33))


## v1.1.0 (2025-03-06)

### Features

- Add ability to give user and group for docker
  ([`acf3b00`](https://github.com/TomasTNunes/VibeBot/commit/acf3b00e7a452765e4d7a577d1e67d77384db815))


## v1.0.0 (2025-03-06)

### Features

- Add control buttons for music message
  ([`8b2dad7`](https://github.com/TomasTNunes/VibeBot/commit/8b2dad7340ec23e8a867bfe4e8feaa749b820852))

- Add debug logs
  ([`38a2644`](https://github.com/TomasTNunes/VibeBot/commit/38a2644dbb1d686b617ed280f992f540e90ef936))

- Add default autoplay and default loop / commands.
  ([`0fefb4c`](https://github.com/TomasTNunes/VibeBot/commit/0fefb4c05f841dad7f3f992bdf8c32ba5cb9dc20))

- Add default volume / command
  ([`ab3a935`](https://github.com/TomasTNunes/VibeBot/commit/ab3a935d19ff1ea0fe43fb7f89ed5b1d0c526e06))

- Add info embed
  ([`0a05e83`](https://github.com/TomasTNunes/VibeBot/commit/0a05e83e2bce92c3e926980b49f45641a314b665))

- Add setup command; music cog app commands handle function; music_data logs
  ([`e6631ae`](https://github.com/TomasTNunes/VibeBot/commit/e6631ae0621a16c407a3c0a94f8392e985c6a9cd))

- Add volume / command; fix: autoplay warning message
  ([`78005ae`](https://github.com/TomasTNunes/VibeBot/commit/78005aecea701f4faff7eca83f63ff5043f34df7))

- Add_to_queue, update music message embed, volume and pause buttons
  ([`09a841b`](https://github.com/TomasTNunes/VibeBot/commit/09a841b3c44a8a40a3b06840993ca326374f8b28))

- Added stop, shuffle and autoplay callbacks. Implemented autoplay. Fix music embed for Lives. Other
  small fixes
  ([`fc88c4d`](https://github.com/TomasTNunes/VibeBot/commit/fc88c4dad3bb1e2107dd22d4ce4093e0d3001973))

- Cleanup music channels at start and handle connect disconnect
  ([`e1c884c`](https://github.com/TomasTNunes/VibeBot/commit/e1c884c9658671a7a1b65142e4fab7236134aa61))

- Delete guild form music data when bot leaves guild
  ([`20705fa`](https://github.com/TomasTNunes/VibeBot/commit/20705fa1c259028433bff0819502be1813a7b7ec))

- Idle task for auto-disconnect and embed warnings
  ([`7f68606`](https://github.com/TomasTNunes/VibeBot/commit/7f6860691277dc82eff4bae4e83f1bcf3a22e359))

- Improve logs; music cog load and unload; music data handle; music join and check
  ([`8ce3fc1`](https://github.com/TomasTNunes/VibeBot/commit/8ce3fc100e4648fe093d13b76fc66b65393b88a1))

- Imrove add music data function
  ([`5d1fe7b`](https://github.com/TomasTNunes/VibeBot/commit/5d1fe7b2c8758a80f0f5c01900c5cacd21b0764d))

- Initialize bot
  ([`fc47b7b`](https://github.com/TomasTNunes/VibeBot/commit/fc47b7ba9cbe2131b94ed14c48e6eb9638f3c7a6))

- Lavalink docker compose yaml file
  ([`b45e147`](https://github.com/TomasTNunes/VibeBot/commit/b45e14777a7ddda2d387007d307162d2596eb731))

- Loop button callback
  ([`5c408e1`](https://github.com/TomasTNunes/VibeBot/commit/5c408e1c8f476a3c1cd653a6d550849f817cd41f))

- Next and previous track buttons callbacks
  ([`810ef8e`](https://github.com/TomasTNunes/VibeBot/commit/810ef8e12a8e4f16f310c0962c822f37029ce1de))

- Playlist add / command and buttons
  ([`e5d7223`](https://github.com/TomasTNunes/VibeBot/commit/e5d72236710f4675fb079356f53289375838131d))

- Playlist add/remove / commands
  ([`3c92e17`](https://github.com/TomasTNunes/VibeBot/commit/3c92e173298c67af3e70507ecc1d9f4695e7e2be))

- Run vibebot in docker ([#2](https://github.com/TomasTNunes/VibeBot/pull/2),
  [`30a1cca`](https://github.com/TomasTNunes/VibeBot/commit/30a1ccad47d6979f7203bb756c28a47043bd58ad))

* chore: rename lavalink docker compose yml

* chore: update logs

* chore: lavalink docker compose identation

* feat: vibebot docker

---------

Co-authored-by: TomasTNunes <tomastrindadenunes@outlook.pt>

- **lavalink**: Add applemuisc with default tokens/keys
  ([`d6e1c26`](https://github.com/TomasTNunes/VibeBot/commit/d6e1c26a2f61ea10387bbf88a00d9e53ea78193e))

- **Lavalink**: Add Lavalink and initial application.yml
  ([`70fecd9`](https://github.com/TomasTNunes/VibeBot/commit/70fecd92386c04eb742ee0cc5e95797f854b9410))

- **music**: Initialize music cogs
  ([`590e1b4`](https://github.com/TomasTNunes/VibeBot/commit/590e1b47ff1b1f1256495961ee16c70296c58afb))
