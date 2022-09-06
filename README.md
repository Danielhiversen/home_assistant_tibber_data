# Tibber Data :zap: 
![Validate with hassfest](https://github.com/Danielhiversen/home_assistant_tibber_custom/workflows/Validate%20with%20hassfest/badge.svg)
[![GitHub Release][releases-shield]][releases]
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Display Tibber data sensors.
Tibber is available in Germany, Norway and Sweden


If you use this link to signup for Tibber, you get 50 euro to buy smart home products in the Tibber store: https://invite.tibber.com/6fd7a447

[Buy me a coffee :)](http://paypal.me/dahoiv)

You get the following sensors:
* Monthly avg price
* Estimated subsidy
* Estimated price with subsidy
* Average of 3 highest hourly consumption (from 3 different days)


## Install
Requires pyTibber >= 0.25.0 and Tibber integration in Home Assistant.
https://hacs.xyz/docs/faq/custom_repositories

## Configuration 

The Tibber component needs to be configured first: https://www.home-assistant.io/integrations/tibber/

In configuration.yaml:

```
tibber_data:
```


[releases]: https://github.com/Danielhiversen/home_assistant_tibber_data/releases
[releases-shield]: https://img.shields.io/github/release/Danielhiversen/home_assistant_tibber_data.svg?style=popout
[downloads-total-shield]: https://img.shields.io/github/downloads/Danielhiversen/home_assistant_tibber_data/total
[hacs-shield]: https://img.shields.io/badge/HACS-Default-orange.svg
[hacs]: https://hacs.xyz/docs/default_repositories
