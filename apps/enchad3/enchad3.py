"""AppDaemon EnChAD3 app.

  @benleb / https://github.com/benleb/ad-ench-ad3

ench:
  module: enchad3
  class: EnChAD3
  exclude:
    - sensor.out_of_order
    - binary_sensor.always_unavailable
  battery
    interval_min: 180
    min_level: 20
  unavailable
    interval_min: 60
  notify: notify.me
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from adutils import ADutils as adu
from fnmatch import fnmatch

try:
    import hassapi as hass  # newer variant
except ImportError:
    import appdaemon.plugins.hass.hassapi as hass  # old variant, will be removed


APP_NAME = "EnChAD3"
APP_ICON = "👩‍⚕️"
APP_VERSION = "0.4.13"

BATTERY_MIN_LEVEL = 20
INTERVAL_BATTERY_MIN = 180
INTERVAL_BATTERY = INTERVAL_BATTERY_MIN / 60

INTERVAL_UNAVAILABLE_MIN = 60
INTERVAL_UNAVAILABLE = INTERVAL_UNAVAILABLE_MIN / 60

INITIAL_DELAY = 12

EXCLUDE = ["binary_sensor.updater", "persistent_notification.config_entry_discovery"]
BAD_STATES = ["unavailable", "unknown"]
LEVEL_ATTRIBUTES = ["battery_level", "Battery Level"]

ICONS = dict(battery="🔋", unavailable="⁉️ ", unknown="❓")


class EnChAD3(hass.Hass):  # type: ignore
    """ench."""

    def initialize(self) -> None:
        """Register API endpoint."""
        self.cfg: Dict[str, Any] = dict()
        self.cfg["notify"] = self.args.get("notify")
        self.cfg["show_friendly_name"] = bool(self.args.get("show_friendly_name", True))
        self.cfg["initial_delay_secs"] = int(
            self.args.get("initial_delay_secs", INITIAL_DELAY)
        )

        # battery check
        if "battery" in self.args:

            battery_cfg = self.args.get("battery")

            # temp. to be compatible with the old interval
            if "interval_min" in battery_cfg:
                interval_min = battery_cfg.get("interval_min")
            elif "interval" in battery_cfg:
                interval_min = battery_cfg.get("interval") * 60
            else:
                interval_min = INTERVAL_BATTERY_MIN

            self.cfg["battery"] = dict(
                interval_min=int(interval_min),
                min_level=int(battery_cfg.get("min_level", BATTERY_MIN_LEVEL)),
            )

            # schedule check
            self.run_every(
                self.check_battery,
                self.datetime() + timedelta(seconds=self.cfg["initial_delay_secs"]),
                self.cfg["battery"]["interval_min"] * 60,
            )

        # unavailable check
        if self.args.get("unavailable"):

            states_cfg = self.args.get("unavailable")

            # temp. to be compatible with the old interval
            if "interval_min" in states_cfg:
                interval_min = states_cfg.get("interval_min")
            elif "interval" in states_cfg:
                interval_min = states_cfg.get("interval") * 60
            else:
                interval_min = INTERVAL_UNAVAILABLE_MIN

            self.cfg["unavailable"] = dict(interval_min=int(interval_min))

            self.run_every(
                self.check_unavailable,
                self.datetime() + timedelta(seconds=self.cfg["initial_delay_secs"]),
                self.cfg["unavailable"]["interval_min"] * 60,
            )

        # merge excluded entities
        exclude = set(EXCLUDE)
        exclude.update([e.lower() for e in self.args.get("exclude", set())])
        self.cfg["exclude"] = sorted(list(exclude))

        # set units
        self.cfg.setdefault(
            "_units", dict(interval="h", interval_min="min", min_level="%")
        )

        # init adutils
        self.adu = adu(APP_NAME, self.cfg, icon=APP_ICON, ad=self, show_config=True)

    def check_battery(self, _: Any) -> None:
        """Handle scheduled checks."""
        results: List[str] = []

        self.adu.log(f"Checking entities for low battery levels...", icon=APP_ICON)

        entities = filter(
            lambda item: not any(fnmatch(item.lower(), pattern) for pattern in self.cfg["exclude"]), self.get_state()
        )

        for entity in sorted(entities):
            battery_level = None
            try:
                # check entities which may be battery level sensors
                if "battery_level" in entity or "battery" in entity:
                    battery_level = int(self._get_vi_state(entity))

                # check entity attributes for battery levels
                if not battery_level:
                    for attr in LEVEL_ATTRIBUTES:
                        battery_level = int(self._get_vi_state(entity, attribute=attr))
                        break
            except (TypeError, ValueError):
                pass

            if battery_level and battery_level <= self.cfg["battery"]["min_level"]:

                results.append(entity)
                self.adu.log(
                    f"{self._name(entity)} has low "
                    f"{adu.hl(f'battery → {adu.hl(int(battery_level))}')}% | "
                    f"last update: {self.last_update(entity)}",
                    icon=ICONS["battery"],
                )

        # send notification
        if self.cfg["notify"] and results:
            self.call_service(
                str(self.cfg["notify"]).replace(".", "/"),
                message=f"{ICONS['battery']} Battery low ({len(results)}): "
                f"{', '.join([e for e in results])}",
            )

        self._print_result("battery", results, "low battery levels")

    def check_unavailable(self, _: Any) -> None:
        """Handle scheduled checks."""
        results: List[str] = []

        self.adu.log(
            f"Checking entities for unavailable/unknown state...", icon=APP_ICON
        )

        entities = filter(
            lambda item: not any(fnmatch(item.lower(), pattern) for pattern in self.cfg["exclude"]), self.get_state()
        )

        for entity in sorted(entities):
            state = None
            try:
                state = self._get_vi_state(entity)
            except TypeError as error:
                self.adu.log(f"Failed to get state for {entity}: {error}")

            if state in BAD_STATES and entity not in results:
                results.append(entity)
                self.adu.log(
                    f"{self._name(entity)} is {adu.hl(state)} | "
                    f"last update: {self.last_update(entity)}",
                    icon=ICONS[state],
                )

        # send notification
        if self.cfg["notify"] and results:
            self.call_service(
                str(self.cfg["notify"]).replace(".", "/"),
                message=f"{APP_ICON} Unavailable entities ({len(results)}): "
                f"{', '.join([e for e in results])}",
            )

        self._print_result("unavailable", results, "unavailable/unknown state")

    def _name(self, entity: str) -> Optional[str]:
        name: Optional[str] = None
        if self.cfg["show_friendly_name"]:
            name = self.friendly_name(entity)
        else:
            name = adu.hl_entity(entity)
        return name

    def _print_result(self, check: str, entities: List[str], reason: str) -> None:
        entites_found = len(entities)
        if entites_found > 0:
            self.adu.log(
                f"{adu.hl(f'{entites_found} entities')} with {adu.hl(reason)}!",
                icon=APP_ICON,
            )
        else:
            self.adu.log(f"no entities with {reason} found", icon=APP_ICON)

    def _get_vi_state(self, entity: str, attribute: Optional[str] = None) -> Any:
        # unified wrapper for get_state in AD3 and AD3
        # will be removed as soon AD4 becomes stable
        if self.adu.appdaemon_v3:
            state = self.get_state(entity=entity, attribute=attribute)
        else:
            state = self.get_state(entity_id=entity, attribute=attribute)
        return state

    # todo  move these methods to adutils lib
    def last_update(self, entity: str) -> Any:
        if self.adu.appdaemon_v3:
            # will be removed as soon AD4 becomes stable
            last_updated = self.get_state(entity=entity, attribute="last_updated")
        else:
            lu_date, lu_time = self._to_localtime(entity, "last_updated")
            last_updated = str(lu_time.strftime("%H:%M:%S"))
            if lu_date != self.date():
                last_updated = f"{last_updated} ({lu_date.strftime('%Y-%m-%d')})"
        return last_updated

    def _to_localtime(self, entity: str, attribute: str) -> Any:
        attributes = self.get_state(entity_id=entity, attribute="all")
        time_utc = datetime.fromisoformat(attributes[attribute])
        tzone = timezone(
            timedelta(minutes=self.get_tz_offset()), name=self.get_timezone()
        )
        time_local = time_utc.astimezone(tzone)
        return (time_local.date(), time_local.time())
