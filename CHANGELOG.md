# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-02-26

### Fixed
- **Snap-back effect**: Temperature/fan sliders now hold optimistic state for 6 seconds instead of immediately reverting to old values
- **Temperature mapping**: Updated sensor names to match Modbus register map correctly:
  - "Температура подачи" → "Температура (точка регулирования)" (INPUT[13])
  - "Температура приточного воздуха" → "Температура подачи (выход установки)" (INPUT[50])
- **Polling optimization**: State updates every 3 seconds, sensors every 30 seconds to reduce network load
- **Error handling**: Added proper error handling for all set commands with optimistic state rollback

### Changed
- Climate entity now shows supply air temperature as current temperature (with fallback to regulation point temperature)
- Added debug logging for temperature and fan speed commands
- Improved UI responsiveness with optimistic updates

## [1.0.0] - 2025-02-25

### Added
- Initial release of Breezart Home Assistant integration
- Full climate entity support with temperature, fan speed, and HVAC modes
- Comprehensive sensor suite (temperature, humidity, CO2, VOC, filters)
- Two-way synchronization with physical remote control
- Native TCP protocol support (port 1560)
- Configuration flow with automatic device discovery
- Full error handling and logging
