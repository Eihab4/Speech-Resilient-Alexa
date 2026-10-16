from botocore.exceptions import ClientError

from config.settings import LocationSettings
from location import AmazonLocationGeocoder, NoGeocoder
from notify import Position

CAIRO = Position(latitude=30.0444, longitude=31.2357)


class FakeGeoPlaces:
    def __init__(self, answer=None, error=None):
        self.answer, self.error, self.calls = answer, error, []

    def reverse_geocode(self, **request):
        self.calls.append(request)
        if self.error:
            raise self.error
        return self.answer


def geocoder(client):
    return AmazonLocationGeocoder(LocationSettings(language="en"), client=client)


def test_the_address_label_comes_back():
    client = FakeGeoPlaces({"ResultItems": [{"Address": {"Label": "Tahrir Square, Cairo, Egypt"}}]})

    assert geocoder(client).address(CAIRO) == "Tahrir Square, Cairo, Egypt"
    assert client.calls == [{"QueryPosition": [31.2357, 30.0444], "MaxResults": 1, "Language": "en"}]


def test_no_result_gives_no_address():
    assert geocoder(FakeGeoPlaces({"ResultItems": []})).address(CAIRO) is None


def test_an_aws_error_gives_no_address_instead_of_failing():
    denied = ClientError({"Error": {"Code": "AccessDeniedException", "Message": "no"}}, "ReverseGeocode")

    assert geocoder(FakeGeoPlaces(error=denied)).address(CAIRO) is None


def test_with_location_turned_off_nothing_is_looked_up():
    assert NoGeocoder().address(CAIRO) is None
