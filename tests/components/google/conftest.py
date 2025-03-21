"""Test configuration and mocks for the google integration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
import datetime
from typing import Any, Generator, TypeVar
from unittest.mock import mock_open, patch

from gcal_sync.auth import API_BASE_URL
from oauth2client.client import Credentials, OAuth2Credentials
import pytest
import yaml

from homeassistant.components.google import CONF_TRACK_NEW, DOMAIN
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.dt import utcnow

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker

ApiResult = Callable[[dict[str, Any]], None]
ComponentSetup = Callable[[], Awaitable[bool]]
_T = TypeVar("_T")
YieldFixture = Generator[_T, None, None]


CALENDAR_ID = "qwertyuiopasdfghjklzxcvbnm@import.calendar.google.com"

# Entities can either be created based on data directly from the API, or from
# the yaml config that overrides the entity name and other settings. A test
# can use a fixture to exercise either case.
TEST_API_ENTITY = "calendar.we_are_we_are_a_test_calendar"
TEST_API_ENTITY_NAME = "We are, we are, a... Test Calendar"
# Name of the entity when using yaml configuration overrides
TEST_YAML_ENTITY = "calendar.backyard_light"
TEST_YAML_ENTITY_NAME = "Backyard Light"

# A calendar object returned from the API
TEST_API_CALENDAR = {
    "id": CALENDAR_ID,
    "etag": '"3584134138943410"',
    "timeZone": "UTC",
    "accessRole": "reader",
    "foregroundColor": "#000000",
    "selected": True,
    "kind": "calendar#calendarListEntry",
    "backgroundColor": "#16a765",
    "description": "Test Calendar",
    "summary": "We are, we are, a... Test Calendar",
    "colorId": "8",
    "defaultReminders": [],
}


@pytest.fixture
def test_api_calendar():
    """Return a test calendar object used in API responses."""
    return TEST_API_CALENDAR


@pytest.fixture
def calendars_config_track() -> bool:
    """Fixture that determines the 'track' setting in yaml config."""
    return True


@pytest.fixture
def calendars_config_ignore_availability() -> bool:
    """Fixture that determines the 'ignore_availability' setting in yaml config."""
    return None


@pytest.fixture
def calendars_config_entity(
    calendars_config_track: bool, calendars_config_ignore_availability: bool | None
) -> dict[str, Any]:
    """Fixture that creates an entity within the yaml configuration."""
    entity = {
        "device_id": "backyard_light",
        "name": "Backyard Light",
        "search": "#Backyard",
        "track": calendars_config_track,
    }
    if calendars_config_ignore_availability is not None:
        entity["ignore_availability"] = calendars_config_ignore_availability
    return entity


@pytest.fixture
def calendars_config(calendars_config_entity: dict[str, Any]) -> list[dict[str, Any]]:
    """Fixture that specifies the calendar yaml configuration."""
    return [
        {
            "cal_id": CALENDAR_ID,
            "entities": [calendars_config_entity],
        }
    ]


@pytest.fixture(autouse=True)
def mock_calendars_yaml(
    hass: HomeAssistant,
    calendars_config: list[dict[str, Any]],
) -> None:
    """Fixture that prepares the google_calendars.yaml mocks."""
    mocked_open_function = mock_open(read_data=yaml.dump(calendars_config))
    with patch("homeassistant.components.google.open", mocked_open_function):
        yield


class FakeStorage:
    """A fake storage object for persiting creds."""

    def __init__(self) -> None:
        """Initialize FakeStorage."""
        self._creds: Credentials | None = None

    def get(self) -> Credentials | None:
        """Get credentials from storage."""
        return self._creds

    def put(self, creds: Credentials) -> None:
        """Put credentials in storage."""
        self._creds = creds


@pytest.fixture
def token_scopes() -> list[str]:
    """Fixture for scopes used during test."""
    return ["https://www.googleapis.com/auth/calendar"]


@pytest.fixture
def token_expiry() -> datetime.datetime:
    """Expiration time for credentials used in the test."""
    return utcnow() + datetime.timedelta(days=7)


@pytest.fixture
def creds(
    token_scopes: list[str], token_expiry: datetime.datetime
) -> OAuth2Credentials:
    """Fixture that defines creds used in the test."""
    return OAuth2Credentials(
        access_token="ACCESS_TOKEN",
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="REFRESH_TOKEN",
        token_expiry=token_expiry,
        token_uri="http://example.com",
        user_agent="n/a",
        scopes=token_scopes,
    )


@pytest.fixture(autouse=True)
def storage() -> YieldFixture[FakeStorage]:
    """Fixture to populate an existing token file for read on startup."""
    storage = FakeStorage()
    with patch("homeassistant.components.google.Storage", return_value=storage):
        yield storage


@pytest.fixture
def config_entry_token_expiry(token_expiry: datetime.datetime) -> float:
    """Fixture for token expiration value stored in the config entry."""
    return token_expiry.timestamp()


@pytest.fixture
def config_entry(
    token_scopes: list[str],
    config_entry_token_expiry: float,
) -> MockConfigEntry:
    """Fixture to create a config entry for the integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "auth_implementation": "device_auth",
            "token": {
                "access_token": "ACCESS_TOKEN",
                "refresh_token": "REFRESH_TOKEN",
                "scope": " ".join(token_scopes),
                "token_type": "Bearer",
                "expires_at": config_entry_token_expiry,
            },
        },
    )


@pytest.fixture
def mock_token_read(
    hass: HomeAssistant,
    creds: OAuth2Credentials,
    storage: FakeStorage,
) -> None:
    """Fixture to populate an existing token file for read on startup."""
    storage.put(creds)


@pytest.fixture
def mock_events_list(
    aioclient_mock: AiohttpClientMocker,
) -> ApiResult:
    """Fixture to construct a fake event list API response."""

    def _put_result(
        response: dict[str, Any], calendar_id: str = None, exc: Exception = None
    ) -> None:
        if calendar_id is None:
            calendar_id = CALENDAR_ID
        aioclient_mock.get(
            f"{API_BASE_URL}/calendars/{calendar_id}/events",
            json=response,
            exc=exc,
        )
        return

    return _put_result


@pytest.fixture
def mock_events_list_items(
    mock_events_list: Callable[[dict[str, Any]], None]
) -> Callable[list[[dict[str, Any]]], None]:
    """Fixture to construct an API response containing event items."""

    def _put_items(items: list[dict[str, Any]]) -> None:
        mock_events_list({"items": items})
        return

    return _put_items


@pytest.fixture
def mock_calendars_list(
    aioclient_mock: AiohttpClientMocker,
) -> ApiResult:
    """Fixture to construct a fake calendar list API response."""

    def _put_result(response: dict[str, Any], exc=None) -> None:
        aioclient_mock.get(
            f"{API_BASE_URL}/users/me/calendarList",
            json=response,
            exc=exc,
        )
        return

    return _put_result


@pytest.fixture
def mock_insert_event(
    aioclient_mock: AiohttpClientMocker,
) -> Callable[[..., dict[str, Any]], None]:
    """Fixture for capturing event creation."""

    def _expect_result(calendar_id: str = CALENDAR_ID) -> None:
        aioclient_mock.post(
            f"{API_BASE_URL}/calendars/{calendar_id}/events",
        )
        return

    return _expect_result


@pytest.fixture(autouse=True)
def set_time_zone(hass):
    """Set the time zone for the tests."""
    # Set our timezone to CST/Regina so we can check calculations
    # This keeps UTC-6 all year round
    hass.config.set_time_zone("America/Regina")


@pytest.fixture
def google_config_track_new() -> None:
    """Fixture for tests to set the 'track_new' configuration.yaml setting."""
    return None


@pytest.fixture
def google_config(google_config_track_new: bool | None) -> dict[str, Any]:
    """Fixture for overriding component config."""
    google_config = {CONF_CLIENT_ID: "client-id", CONF_CLIENT_SECRET: "client-secret"}
    if google_config_track_new is not None:
        google_config[CONF_TRACK_NEW] = google_config_track_new
    return google_config


@pytest.fixture
def config(google_config: dict[str, Any]) -> dict[str, Any]:
    """Fixture for overriding component config."""
    return {DOMAIN: google_config} if google_config else {}


@pytest.fixture
def component_setup(hass: HomeAssistant, config: dict[str, Any]) -> ComponentSetup:
    """Fixture for setting up the integration."""

    async def _setup_func() -> bool:
        result = await async_setup_component(hass, DOMAIN, config)
        await hass.async_block_till_done()
        return result

    return _setup_func
