# Tibber Data :zap: 
![Validate with hassfest](https://github.com/Danielhiversen/home_assistant_tibber_data/workflows/Validate%20with%20hassfest/badge.svg)
[![GitHub Release][releases-shield]][releases]
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Display Tibber data sensors.
Tibber is available in Germany, Norway and Sweden


If you use this link to signup for Tibber, you get 50 euro to buy smart home products in the Tibber store: https://invite.tibber.com/6fd7a447

[Buy me a coffee :)](http://paypal.me/dahoiv)

You get the following sensors:
* Monthly avg price
* Monthly avg customer price (Your price calculated as your consumption divided by your cost this month)
* Estimated subsidy
* Estimated price with subsidy
* Average of 3 highest hourly consumption (from 3 different days)
* Monthly accumulated cost with subsidy
* Daily accumulated cost with subsidy (only available if you have a real-time meter, Tibber Pulse)
* Monthly production profit
* Daily production profit (only available if you have a real-time meter, Tibber Pulse)
* Daily production profit (only available if you have a real-time meter, Tibber Pulse)
* Yearly consumption
* Monthly consumption compared to last year, this month consumption compared to same days last year

Experimental and requires additional configuration:
* Grid price (Only if your grid company is supported by Tibber)
* Estimated total price with subsidy and grid price (Only if your grid company is supported by Tibber)
* Charger cost day (Requires a connected charger, like Easee or Zaptec)
* Charger cost month (Requires a connected charger, like Easee or Zaptec)
* Charger consumption day (Requires a connected charger, like Easee or Zaptec)
* Charger consumption month (Requires a connected charger, like Easee or Zaptec)



## Install
Requires Tibber integration in Home Assistant.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Danielhiversen&repository=home_assistant_tibber_data&category=integration)

## Configuration 

The Tibber component needs to be configured first: https://www.home-assistant.io/integrations/tibber/

In configuration.yaml:

```
tibber_data:
```


Optional for extra sensors:

```
tibber_data:
  email: Your email registred at Tibber
  password: Your Tibber password
```

[releases]: https://github.com/Danielhiversen/home_assistant_tibber_data/releases
[releases-shield]: https://img.shields.io/github/release/Danielhiversen/home_assistant_tibber_data.svg?style=popout
[downloads-total-shield]: https://img.shields.io/github/downloads/Danielhiversen/home_assistant_tibber_data/total
[hacs-shield]: https://img.shields.io/badge/HACS-Default-orange.svg
[hacs]: https://hacs.xyz/docs/default_repositories
