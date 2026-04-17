# Changelog

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
