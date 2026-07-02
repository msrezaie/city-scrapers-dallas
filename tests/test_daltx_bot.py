from datetime import datetime
from os.path import dirname, join

import pytest
from city_scrapers_core.constants import BOARD, COMMITTEE, TENTATIVE
from city_scrapers_core.utils import file_response
from freezegun import freeze_time
from scrapy.http import XmlResponse

from city_scrapers.spiders.daltx_bot import DaltxBotSpider

with open(join(dirname(__file__), "files", "daltx_bot_sitemap.xml"), "rb") as f:
    sitemap = XmlResponse(
        url="https://www.dallascollege.edu/sitemap.xml", body=f.read()
    )

details_page = file_response(
    join(dirname(__file__), "files", "daltx_bot_details_page_example.html"),
    url="https://www.dallascollege.edu/events/trustees/2026/jun-2-board-meeting---regular/",  # noqa
)

# Committee page: exercises COMMITTEE classification plus agenda-PDF and
# /media/ video links (and exclusion of the generic mediaportal home link).
committee_page = file_response(
    join(dirname(__file__), "files", "daltx_bot_committee_example.html"),
    url="https://www.dallascollege.edu/events/trustees/2026/feb-3-board-meeting---finance-committee/",  # noqa
)


@pytest.fixture
def spider():
    return DaltxBotSpider()


@pytest.fixture
def request_items(spider):
    return [request for request in spider.parse(sitemap)]


@pytest.fixture
def parsed_item(spider):
    with freeze_time("2026-05-13"):
        return next(spider._parse_detail(details_page))


@pytest.fixture
def parsed_committee(spider):
    with freeze_time("2026-01-15"):
        return next(spider._parse_detail(committee_page))


def test_count(request_items):
    # 28 detail pages in the sitemap for 2026
    assert len(request_items) == 28


def test_request_urls(request_items):
    assert all("/events/trustees/" in r.url for r in request_items)
    assert not any(r.url.rstrip("/").endswith(("2026", "2025")) for r in request_items)


def test_title(parsed_item):
    assert parsed_item["title"] == "June Board Meeting - Regular"


def test_description(parsed_item):
    assert parsed_item["description"] == ""


def test_start(parsed_item):
    assert parsed_item["start"] == datetime(2026, 6, 2, 16, 0)


def test_end(parsed_item):
    assert parsed_item["end"] == datetime(2026, 6, 2, 17, 0)


def test_time_notes(parsed_item):
    assert parsed_item["time_notes"] == ""


def test_id(parsed_item):
    assert (
        parsed_item["id"]
        == "daltx_bot/202606021600/x/june_board_meeting_regular"  # noqa
    )


def test_status(parsed_item):
    assert parsed_item["status"] == TENTATIVE


def test_location(parsed_item):
    assert parsed_item["location"] == {
        "name": "Administrative Office",
        "address": "1601 Botham Jean Blvd., Dallas TX 75215",
    }


def test_source(parsed_item):
    assert (
        parsed_item["source"]
        == "https://www.dallascollege.edu/events/trustees/2026/jun-2-board-meeting---regular/"  # noqa
    )


def test_links(parsed_item):
    assert parsed_item["links"] == [
        {
            "href": "https://www.dallascollege.edu/events/trustees/2026/jun-2-board-meeting---regular/",  # noqa
            "title": "Meeting Details",
        },
    ]


def test_classification(parsed_item):
    assert parsed_item["classification"] == BOARD


def test_committee_classification(parsed_committee):
    assert parsed_committee["classification"] == COMMITTEE


def test_committee_start_end(parsed_committee):
    assert parsed_committee["start"] == datetime(2026, 2, 3, 9, 30)
    assert parsed_committee["end"] == datetime(2026, 2, 3, 14, 0)
    assert parsed_committee["all_day"] is False


def test_committee_links(parsed_committee):
    # Meeting Details + agenda PDF + the /media/ recording; the generic
    # mediaportal.dallascollege.edu/ home link is excluded.
    assert parsed_committee["links"] == [
        {
            "href": "https://www.dallascollege.edu/events/trustees/2026/feb-3-board-meeting---finance-committee/",  # noqa
            "title": "Meeting Details",
        },
        {
            "href": "https://www.dallascollege.edu/media/dallas-college/content-assets/documents/about-dallas-college/board-of-trustees/agendas/2026/2026FEB3_Finance.Committee_Agenda_certified.pdf",  # noqa
            "title": "Feb. 3 Board Meeting: Finance Committee agenda (PDF - 2MB)",
        },
        {
            "href": "https://mediaportal.dallascollege.edu/media/EDKoRD",
            "title": "Live Streaming Of Board Meeting",
        },
    ]
