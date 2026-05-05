# Changelog

## [1.10.1](https://github.com/d0ugal/homeassistant-trinity/compare/v1.10.0...v1.10.1) (2026-05-05)


### Bug Fixes

* run ruff format check directly to avoid output-format flag issue ([a310a3c](https://github.com/d0ugal/homeassistant-trinity/commit/a310a3cd22b5bfd3fd0bae2249cce6d8ccda1c32))

## [1.10.0](https://github.com/d0ugal/homeassistant-trinity/compare/v1.9.3...v1.10.0) (2026-05-03)


### Features

* add url and line1/line2 support to display_image service ([53b6ef5](https://github.com/d0ugal/homeassistant-trinity/commit/53b6ef5563b130191a70138b68e9e9849e525070))


### Bug Fixes

* remove unused alias in _finalize closure ([5b83fe2](https://github.com/d0ugal/homeassistant-trinity/commit/5b83fe242809aceb8b5fde8f4bbcf72479e2567f))

## [1.9.3](https://github.com/d0ugal/homeassistant-trinity/compare/v1.9.2...v1.9.3) (2026-04-30)


### Bug Fixes

* discard in-flight snapshots after cancel_stream() is called ([60478ee](https://github.com/d0ugal/homeassistant-trinity/commit/60478eee31bd5d2fc4aba2b1c92d0c419fe18baa))

## [1.9.2](https://github.com/d0ugal/homeassistant-trinity/compare/v1.9.1...v1.9.2) (2026-04-29)


### Bug Fixes

* persist emoji overlay params (line1, line2, corner) across reverts ([c70151b](https://github.com/d0ugal/homeassistant-trinity/commit/c70151bbe15d9dd229d0096f8395c90a138df19e))
* use aiohttp.ClientTimeout in _fetch_image_url instead of bare int ([d8faaf5](https://github.com/d0ugal/homeassistant-trinity/commit/d8faaf50a026aa441a67bf5f12e5d5c98c9d2184))

## [1.9.1](https://github.com/d0ugal/homeassistant-trinity/compare/v1.9.0...v1.9.1) (2026-04-28)


### Bug Fixes

* replace deprecated get_event_loop() with get_running_loop() in _stream_loop ([ffde4e8](https://github.com/d0ugal/homeassistant-trinity/commit/ffde4e8ce2a2d8235c1653357abfce6b22845d96))

## [1.9.0](https://github.com/d0ugal/homeassistant-trinity/compare/v1.8.0...v1.9.0) (2026-04-27)


### Features

* bridge display_stream into do_display_url until first PyAV frame arrives ([16045d1](https://github.com/d0ugal/homeassistant-trinity/commit/16045d12e26975102e13a3686d4a2e37d68cbd31))

## [1.8.0](https://github.com/d0ugal/homeassistant-trinity/compare/v1.7.1...v1.8.0) (2026-04-23)


### Features

* add media_player platform for camera.play_stream support ([416225f](https://github.com/d0ugal/homeassistant-trinity/commit/416225fc61674c71e5c086cfcec1b25e8f1c03c5))
* input_select.trinity_crop controls stream crop position ([21de4d1](https://github.com/d0ugal/homeassistant-trinity/commit/21de4d107e90a2279adc7182a946313778aca2cb))


### Bug Fixes

* apply ruff formatting ([ed8a668](https://github.com/d0ugal/homeassistant-trinity/commit/ed8a6683866bc20acb1d47289e4e6ca058a037a2))
* apply ruff formatting to __init__.py ([cb72629](https://github.com/d0ugal/homeassistant-trinity/commit/cb72629d06c37b44dc26a7d6fecb78801424a9a8))
* fire stream-end callback when cancel_stream() is called externally ([1aea734](https://github.com/d0ugal/homeassistant-trinity/commit/1aea734a3113fe7a0d941c97e5f3cf5a161d6571))
* remove unused loop variable flagged by ruff ([c03ea09](https://github.com/d0ugal/homeassistant-trinity/commit/c03ea0913c8ff86c1cd91383bdaf2cc39a6d5c0b))
* stream cancellation race condition and callback ordering ([5eb27d9](https://github.com/d0ugal/homeassistant-trinity/commit/5eb27d933f93269be655e7bed395736ab79fce9a))
* write playing state before awaiting stream start ([9673fe9](https://github.com/d0ugal/homeassistant-trinity/commit/9673fe944a236f6c62878a0c9a19321ab78d7994))


### Documentation

* update README for media player entity and crop anchors ([d260825](https://github.com/d0ugal/homeassistant-trinity/commit/d2608259cc3b284e48506ee2facaced8c46063d1))

## [1.7.1](https://github.com/d0ugal/homeassistant-trinity/compare/v1.7.0...v1.7.1) (2026-04-21)


### Bug Fixes

* update corner description to bottom-right and 2x scale ([9c44883](https://github.com/d0ugal/homeassistant-trinity/commit/9c448837c852138e58dbdb5c18a6b84fa53c2168))

## [1.7.0](https://github.com/d0ugal/homeassistant-trinity/compare/v1.6.0...v1.7.0) (2026-04-21)


### Features

* add corner parameter to display_emoji for trend indicator ([1334fc6](https://github.com/d0ugal/homeassistant-trinity/commit/1334fc6552288fb290d54ece717b6d1a7076252b))

## [1.6.0](https://github.com/d0ugal/homeassistant-trinity/compare/v1.5.0...v1.6.0) (2026-04-17)


### Features

* brightness control via MQTT and trinity.set_brightness service ([0d454b4](https://github.com/d0ugal/homeassistant-trinity/commit/0d454b45cca2fccad017a8c20b122601fc05dd60))


### Bug Fixes

* apply ruff format and fix en-dash in brightness docstring ([f616987](https://github.com/d0ugal/homeassistant-trinity/commit/f6169875e37efc1139cc363fbd0619f51764fbd7))
* enable CIE1931 gamma correction in ESPHome config ([3cfc3ed](https://github.com/d0ugal/homeassistant-trinity/commit/3cfc3edf6a2286939261d5c2607beec7d21438ec))
* set explicit bit_depth 6 in ESPHome config ([87f5070](https://github.com/d0ugal/homeassistant-trinity/commit/87f5070eb52a35e9586911e5f59cb25b76a9c3d1))

## [1.5.0](https://github.com/d0ugal/homeassistant-trinity/compare/v1.4.0...v1.5.0) (2026-04-16)


### Features

* display_for, display_emoji, persistent default, and crop anchor ([cabdbce](https://github.com/d0ugal/homeassistant-trinity/commit/cabdbcee8e221209803c91e5b2b53ec4e989511e))


### Bug Fixes

* add esphome config with correct RGB565 to RGB888 bit-replication ([b19b32e](https://github.com/d0ugal/homeassistant-trinity/commit/b19b32e45ea06483da71dfaebe0ba93ed74e5f93))
* revert config_flow method signature to single line (ruff format) ([5a93d57](https://github.com/d0ugal/homeassistant-trinity/commit/5a93d572a94c9bf293840cbd0b88a0b890c10efe))

## [1.4.0](https://github.com/d0ugal/homeassistant-trinity/compare/v1.3.0...v1.4.0) (2026-04-10)


### Features

* add crop anchor to display_stream service ([f90d3a0](https://github.com/d0ugal/homeassistant-trinity/commit/f90d3a006cd649739973122e6b034d994d5f69e9))

## [1.3.0](https://github.com/d0ugal/homeassistant-trinity/compare/v1.2.0...v1.3.0) (2026-04-08)


### Features

* render moon image in greyscale ([af1eec1](https://github.com/d0ugal/homeassistant-trinity/commit/af1eec18c0907701ffda3fbf840306657f1cad2e))

## [1.2.0](https://github.com/d0ugal/homeassistant-trinity/compare/v1.1.0...v1.2.0) (2026-04-07)


### Features

* add display_emoji service ([21d7818](https://github.com/d0ugal/homeassistant-trinity/commit/21d78182984c49c3c1b6ca356592789a87955faf))


### Bug Fixes

* replace multiplication sign in docstring to pass RUF002 ([011df3a](https://github.com/d0ugal/homeassistant-trinity/commit/011df3a1d344a0900cbd297ca48aa0c1dc77c418))


### Documentation

* add display_emoji service to README ([0bb83c9](https://github.com/d0ugal/homeassistant-trinity/commit/0bb83c9787c8eed3af8e1fca5d92142e87238f0a))

## [1.1.0](https://github.com/d0ugal/homeassistant-trinity/compare/v1.0.0...v1.1.0) (2026-04-07)


### Features

* add priority/revert system matching iDotMatrix ([d20deab](https://github.com/d0ugal/homeassistant-trinity/commit/d20deabcf6024f7d5f947c945c79d855e116d501))
* display_image supports image.* entities ([afed5d6](https://github.com/d0ugal/homeassistant-trinity/commit/afed5d649c357cdefe04e2421027e5346e3a0f5e))
* initial Trinity custom integration ([60e6dd9](https://github.com/d0ugal/homeassistant-trinity/commit/60e6dd90283031e42ef852c015b449c1b27966a4))


### Bug Fixes

* apply ruff formatting ([82ca52e](https://github.com/d0ugal/homeassistant-trinity/commit/82ca52ee9149e2f5f6146a3c467c029678871d43))
* resolve ruff lint errors in coordinator ([9acbd2e](https://github.com/d0ugal/homeassistant-trinity/commit/9acbd2ee3dd3763a253077d0ae00e37774956a5b))
* sort imports in coordinator, add brand icon for HACS ([a16a374](https://github.com/d0ugal/homeassistant-trinity/commit/a16a374e350501e6607349bb8b10fea8cdae55b1))


### Documentation

* add ESPHome config, screenshots, and expand README ([d610a15](https://github.com/d0ugal/homeassistant-trinity/commit/d610a153e50a171eb1989460b27d27ea4d43b722))
