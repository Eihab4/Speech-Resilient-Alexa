import logging
from typing import Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from config import Settings
from config.settings import LocationSettings
from messages import ErrorMessage
from notify import Position

logger = logging.getLogger(__name__)


class Geocoder(Protocol):
    def address(self, position: Position) -> str | None:
        """A readable address for the position, or None. Never raises: an alert goes out without one."""


class NoGeocoder:
    def address(self, position: Position) -> str | None:
        return None


class AmazonLocationGeocoder:
    def __init__(self, settings: LocationSettings, client=None) -> None:
        self._settings = settings
        # One short try: the alert is waiting.
        config = Config(
            connect_timeout=settings.timeout_seconds,
            read_timeout=settings.timeout_seconds,
            retries={"max_attempts": 1},
        )
        self._client = client or boto3.client("geo-places", region_name=settings.region, config=config)

    def address(self, position: Position) -> str | None:
        try:
            response = self._client.reverse_geocode(
                QueryPosition=[position.longitude, position.latitude],  # longitude first
                MaxResults=1,
                Language=self._settings.language,
            )
        except (BotoCoreError, ClientError):
            logger.exception(ErrorMessage.LOCATION_UNAVAILABLE)
            return None
        items = response.get("ResultItems") or []
        return items[0].get("Address", {}).get("Label") if items else None


def create_geocoder(settings: Settings) -> Geocoder:
    return AmazonLocationGeocoder(settings.location) if settings.location.enabled else NoGeocoder()
