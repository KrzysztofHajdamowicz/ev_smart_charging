"""Test ev_smart_charging coordinator."""

from datetime import datetime

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_ON, STATE_OFF, MAJOR_VERSION, MINOR_VERSION
from homeassistant.helpers.entity_registry import async_get as async_entity_registry_get
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.util import dt as dt_util

from custom_components.ev_smart_charging import async_setup_entry
from custom_components.ev_smart_charging.coordinator import (
    EVSmartChargingCoordinator,
)
from custom_components.ev_smart_charging.const import DOMAIN

from tests.helpers.helpers import (
    MockChargerEntity,
    MockPriceEntity,
    MockSOCEntity,
    MockTargetSOCEntity,
)
from tests.price import PRICE_20221001, PRICE_20221002
from tests.coordinator.const import (
    MOCK_CONFIG_START_QUARTER_2A,
    MOCK_CONFIG_START_QUARTER_2B,
    MOCK_CONFIG_START_QUARTER_2C,
)


# pylint: disable=unused-argument
async def test_coordinator_start_hour_end_before_start_2a(
    hass: HomeAssistant, skip_service_calls, set_cet_timezone, freezer
):
    """Test Coordinator."""

    # Continuous charging

    # end < start
    # - both am
    # -- now before end, before start, after start am, after start pm <===
    # - end am, start pm
    # -- now before end, before start am, before start pm, after start
    # - both pm
    # -- now before end am, before end pm, before start, after start

    freezer.move_to("2022-10-01T02:00:00+02:00")

    entity_registry: EntityRegistry = async_entity_registry_get(hass)
    MockSOCEntity.create(hass, entity_registry, "65")
    MockTargetSOCEntity.create(hass, entity_registry, "80")
    MockPriceEntity.create(hass, entity_registry, 123)
    MockChargerEntity.create(hass, entity_registry, STATE_OFF)
    MockPriceEntity.set_state(hass, PRICE_20221001, None)
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_START_QUARTER_2A, entry_id="test"
    )
    if MAJOR_VERSION > 2024 or (MAJOR_VERSION == 2024 and MINOR_VERSION >= 7):
        config_entry.mock_state(hass=hass, state=ConfigEntryState.LOADED)
    config_entry.add_to_hass(hass)
    assert await async_setup_entry(hass, config_entry)
    await hass.async_block_till_done()
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][config_entry.entry_id], EVSmartChargingCoordinator
    )
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator is not None
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await coordinator.switch_apply_limit_update(False)
    await coordinator.switch_continuous_update(True)
    await coordinator.switch_ev_connected_update(True)
    await coordinator.switch_keep_on_update(False)
    await hass.async_block_till_done()

    # Start_hour = 12:00, Ready_hour = 03:00
    # 5 hours => 02:00-03:00
    assert coordinator.auto_charging_state == STATE_ON
    assert coordinator.sensor.state == STATE_ON
    assert coordinator.sensor.charging_is_planned is True
    assert coordinator.sensor.charging_start_time == datetime(
        2022, 10, 1, 2, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_stop_time == datetime(
        2022, 10, 1, 3, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_number_of_quarters == 1 * 4

    # Start_hour = 12:00, Ready_hour = 03:00
    # 5 hours => None
    freezer.move_to("2022-10-01T10:00:00+02:00")
    MockSOCEntity.set_state(hass, "67")
    await coordinator.switch_active_update(False)
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await hass.async_block_till_done()
    assert coordinator.auto_charging_state == STATE_OFF
    assert coordinator.sensor.state == STATE_OFF
    assert coordinator.sensor.charging_is_planned is False
    assert coordinator.sensor.charging_start_time is None
    assert coordinator.sensor.charging_stop_time is None
    assert coordinator.sensor.charging_number_of_quarters == 0

    # Start_hour = 12:00, Ready_hour = 03:00
    # 5 hours => 22:00-03:00
    freezer.move_to("2022-10-01T14:00:00+02:00")
    MockPriceEntity.set_state(hass, PRICE_20221001, PRICE_20221002)
    MockSOCEntity.set_state(hass, "65")
    await coordinator.switch_active_update(False)
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await hass.async_block_till_done()
    assert coordinator.auto_charging_state == STATE_OFF
    assert coordinator.sensor.state == STATE_OFF
    assert coordinator.sensor.charging_is_planned is True
    assert coordinator.sensor.charging_start_time == datetime(
        2022, 10, 1, 22, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_stop_time == datetime(
        2022, 10, 2, 3, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_number_of_quarters == 5 * 4

    # Start_hour = 12:00, Ready_hour = 03:00
    # 5 hours => 23:00-03:00
    freezer.move_to("2022-10-01T23:00:00+02:00")
    MockSOCEntity.set_state(hass, "68")
    await coordinator.switch_active_update(False)
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await hass.async_block_till_done()
    assert coordinator.auto_charging_state == STATE_ON
    assert coordinator.sensor.state == STATE_ON
    assert coordinator.sensor.charging_is_planned is True
    assert coordinator.sensor.charging_start_time == datetime(
        2022, 10, 1, 23, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_stop_time == datetime(
        2022, 10, 2, 3, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_number_of_quarters == 4 * 4

    # Unsubscribe to listeners
    coordinator.unsubscribe_listeners()


async def test_coordinator_start_hour_end_before_start_2b(
    hass: HomeAssistant, skip_service_calls, set_cet_timezone, freezer
):
    """Test Coordinator."""

    # Continuous charging

    # end < start
    # - both am
    # -- now before end, before start, after start am, after start pm
    # - end am, start pm
    # -- now before end, before start am, before start pm, after start <===
    # - both pm
    # -- now before end am, before end pm, before start, after start

    freezer.move_to("2022-10-01T02:00:00+02:00")

    entity_registry: EntityRegistry = async_entity_registry_get(hass)
    MockSOCEntity.create(hass, entity_registry, "65")
    MockTargetSOCEntity.create(hass, entity_registry, "80")
    MockPriceEntity.create(hass, entity_registry, 123)
    MockChargerEntity.create(hass, entity_registry, STATE_OFF)
    MockPriceEntity.set_state(hass, PRICE_20221001, None)
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_START_QUARTER_2B, entry_id="test"
    )
    if MAJOR_VERSION > 2024 or (MAJOR_VERSION == 2024 and MINOR_VERSION >= 7):
        config_entry.mock_state(hass=hass, state=ConfigEntryState.LOADED)
    config_entry.add_to_hass(hass)
    assert await async_setup_entry(hass, config_entry)
    await hass.async_block_till_done()
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][config_entry.entry_id], EVSmartChargingCoordinator
    )
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator is not None
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await coordinator.switch_apply_limit_update(False)
    await coordinator.switch_continuous_update(True)
    await coordinator.switch_ev_connected_update(True)
    await coordinator.switch_keep_on_update(False)
    await hass.async_block_till_done()

    # Start_hour = 22:00, Ready_hour = 09:00
    # 5 hours => 03:00-08:00
    assert coordinator.auto_charging_state == STATE_OFF
    assert coordinator.sensor.state == STATE_OFF
    assert coordinator.sensor.charging_is_planned is True
    assert coordinator.sensor.charging_start_time == datetime(
        2022, 10, 1, 3, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_stop_time == datetime(
        2022, 10, 1, 8, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_number_of_quarters == 5 * 4

    # Start_hour = 22:00, Ready_hour = 09:00
    # 5 hours => None
    freezer.move_to("2022-10-01T12:00:00+02:00")
    MockSOCEntity.set_state(hass, "67")
    await coordinator.switch_active_update(False)
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await hass.async_block_till_done()
    assert coordinator.auto_charging_state == STATE_OFF
    assert coordinator.sensor.state == STATE_OFF
    assert coordinator.sensor.charging_is_planned is False
    assert coordinator.sensor.charging_start_time is None
    assert coordinator.sensor.charging_stop_time is None
    assert coordinator.sensor.charging_number_of_quarters == 0

    # Start_hour = 22:00, Ready_hour = 09:00
    # 5 hours => 03:00-08:00
    freezer.move_to("2022-10-01T14:00:00+02:00")
    MockPriceEntity.set_state(hass, PRICE_20221001, PRICE_20221002)
    MockSOCEntity.set_state(hass, "65")
    await coordinator.switch_active_update(False)
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await hass.async_block_till_done()
    assert coordinator.auto_charging_state == STATE_OFF
    assert coordinator.sensor.state == STATE_OFF
    assert coordinator.sensor.charging_is_planned is True
    assert coordinator.sensor.charging_start_time == datetime(
        2022, 10, 2, 3, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_stop_time == datetime(
        2022, 10, 2, 8, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_number_of_quarters == 5 * 4

    # Start_hour = 22:00, Ready_hour = 09:00
    # 5 hours => 03:00-08:00
    freezer.move_to("2022-10-01T23:00:00+02:00")
    MockSOCEntity.set_state(hass, "65")
    await coordinator.switch_active_update(False)
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await hass.async_block_till_done()
    assert coordinator.auto_charging_state == STATE_OFF
    assert coordinator.sensor.state == STATE_OFF
    assert coordinator.sensor.charging_is_planned is True
    assert coordinator.sensor.charging_start_time == datetime(
        2022, 10, 2, 3, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_stop_time == datetime(
        2022, 10, 2, 8, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_number_of_quarters == 5 * 4

    # Unsubscribe to listeners
    coordinator.unsubscribe_listeners()


async def test_coordinator_start_hour_end_before_start_2c(
    hass: HomeAssistant, skip_service_calls, set_cet_timezone, freezer
):
    """Test Coordinator."""

    # Continuous charging

    # end < start
    # - both am
    # -- now before end, before start, after start am, after start pm
    # - end am, start pm
    # -- now before end, before start am, before start pm, after start
    # - both pm
    # -- now before end am, before end pm, before start, after start <===

    freezer.move_to("2022-10-01T02:00:00+02:00")

    entity_registry: EntityRegistry = async_entity_registry_get(hass)
    MockSOCEntity.create(hass, entity_registry, "65")
    MockTargetSOCEntity.create(hass, entity_registry, "80")
    MockPriceEntity.create(hass, entity_registry, 123)
    MockChargerEntity.create(hass, entity_registry, STATE_OFF)
    MockPriceEntity.set_state(hass, PRICE_20221001, None)
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_START_QUARTER_2C, entry_id="test"
    )
    if MAJOR_VERSION > 2024 or (MAJOR_VERSION == 2024 and MINOR_VERSION >= 7):
        config_entry.mock_state(hass=hass, state=ConfigEntryState.LOADED)
    config_entry.add_to_hass(hass)
    assert await async_setup_entry(hass, config_entry)
    await hass.async_block_till_done()
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][config_entry.entry_id], EVSmartChargingCoordinator
    )
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator is not None
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await coordinator.switch_apply_limit_update(False)
    await coordinator.switch_continuous_update(True)
    await coordinator.switch_ev_connected_update(True)
    await coordinator.switch_keep_on_update(False)
    await hass.async_block_till_done()

    # Start_hour = 22:00, Ready_hour = 15:00
    # 5 hours => 03:00-´08:00
    assert coordinator.auto_charging_state == STATE_OFF
    assert coordinator.sensor.state == STATE_OFF
    assert coordinator.sensor.charging_is_planned is True
    assert coordinator.sensor.charging_start_time == datetime(
        2022, 10, 1, 3, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_stop_time == datetime(
        2022, 10, 1, 8, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_number_of_quarters == 5 * 4

    # Start_hour = 22:00, Ready_hour = 15:00
    # 1 hours => 14:00-15:00
    freezer.move_to("2022-10-01T14:00:00+02:00")
    MockPriceEntity.set_state(hass, PRICE_20221001, PRICE_20221002)
    MockSOCEntity.set_state(hass, "67")
    await coordinator.switch_active_update(False)
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await hass.async_block_till_done()
    assert coordinator.auto_charging_state == STATE_ON
    assert coordinator.sensor.state == STATE_ON
    assert coordinator.sensor.charging_is_planned is True
    assert coordinator.sensor.charging_start_time == datetime(
        2022, 10, 1, 14, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_stop_time == datetime(
        2022, 10, 1, 15, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_number_of_quarters == 1 * 4

    # Start_hour = 22:00, Ready_hour = 15:00
    # 5 hours => 03:00-08:00
    freezer.move_to("2022-10-01T18:00:00+02:00")
    MockSOCEntity.set_state(hass, "65")
    await coordinator.switch_active_update(False)
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await hass.async_block_till_done()
    assert coordinator.auto_charging_state == STATE_OFF
    assert coordinator.sensor.state == STATE_OFF
    assert coordinator.sensor.charging_is_planned is True
    assert coordinator.sensor.charging_start_time == datetime(
        2022, 10, 2, 3, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_stop_time == datetime(
        2022, 10, 2, 8, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_number_of_quarters == 5 * 4

    # Start_hour = 22:00, Ready_hour = 15:00
    # 5 hours => 17:00-22:00
    freezer.move_to("2022-10-01T23:00:00+02:00")
    MockSOCEntity.set_state(hass, "65")
    await coordinator.switch_active_update(False)
    await hass.async_block_till_done()
    await coordinator.switch_active_update(True)
    await hass.async_block_till_done()
    assert coordinator.auto_charging_state == STATE_OFF
    assert coordinator.sensor.state == STATE_OFF
    assert coordinator.sensor.charging_is_planned is True
    assert coordinator.sensor.charging_start_time == datetime(
        2022, 10, 2, 3, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_stop_time == datetime(
        2022, 10, 2, 8, 0, tzinfo=dt_util.get_time_zone("Europe/Stockholm")
    )
    assert coordinator.sensor.charging_number_of_quarters == 5 * 4

    # Unsubscribe to listeners
    coordinator.unsubscribe_listeners()
