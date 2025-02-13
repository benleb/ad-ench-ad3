# EnCh - Entity Checker | AppDaemon 3.x Edition

*EnCh is an [AppDaemon](https://github.com/home-assistant/appdaemon) app which checks the `battery_level` and/or state (`unknown` or `unavailable` currently) of Home Assistant entities and sends a notification if desired.*

**IF YOU RUN APPDAEMON >=4.x (also Betas/dev Branch) CONSIDER USING THE MUCH FASTER [ad-ench](https://github.com/benleb/ad-ench)!**

## Installation

Use [HACS](https://github.com/custom-components/hacs) or [download](https://github.com/benleb/ad-ench-ad3/releases) the `enchad3` directory from inside the `apps` directory here to your local `apps` directory, then add the configuration to enable the `enchad3` module.

## App configuration

Here's an exemplary configuration for this app (to be added to AppDaemon's configuration file, typically `apps.yaml`). Adjust the values as you wish.

```yaml
ench:
  module: enchad3
  class: EnChAD3
  notify: "notify.mobile_app"
  show_friendly_name: False
  exclude:
    - sensor.out_of_order
    - binary_sensor.always_unavailable
  battery:
    interval_min: 180
    min_level: 20
  unavailable:
    interval_min: 60
```

### Configuration

key | optional | type | default | description
-- | -- | -- | -- | --
`module` | False | string | ench | The module name of the app.
`class` | False | string | EnCh | The name of the python class.
`notify` | True | string | | The Home Assistant service used for notification
`initial_delay_secs` | True | int | 120 | Time to wait before first checks. This grace-period is necessary to give slow devices and integrations in Home Assistant a chance to become "available".
`exclude` | True | list | | Excluded entities. Supports wildcard/patterns via [fnmatch](https://docs.python.org/3/library/fnmatch.html)
`battery` | True | map | | Set to enable low battery check
`unavailable` | True | map | | Set to enable unavailable state check

#### Battery configuration

key | optional | type | default | description
-- | -- | -- | -- | --
`min_level` | True | integer | 20 | Minimum battery level a entity should have
`interval_min` | True | integer | 180 | Minutes between checks

#### Unavailable/unknown state configuration

key | optional | type | default | description
-- | -- | -- | -- | --
`interval_min` | True | integer | 60 | Minutes between checks
