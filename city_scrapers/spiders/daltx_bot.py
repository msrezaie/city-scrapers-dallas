import re
from datetime import datetime

from city_scrapers_core.constants import BOARD, COMMITTEE
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from dateutil.parser import parse as date_parser


class DaltxBotSpider(CityScrapersSpider):
    name = "daltx_bot"
    agency = "Dallas College Board of Trustees"
    timezone = "America/Chicago"

    start_urls = ["https://www.dallascollege.edu/sitemap.xml"]

    video_param = "mediaportal.dallascollege.edu/media/"

    detail_re = re.compile(r"/events/trustees/\d{4}/[^/]+/?$")

    def parse(self, response):
        response.selector.remove_namespaces()

        detail_urls = response.xpath("//loc/text()").getall()
        for url in detail_urls:
            if self.detail_re.search(url):
                yield response.follow(
                    url=response.urljoin(url),
                    callback=self._parse_detail,
                )

    def _parse_detail(self, response):
        start, end, all_day = self._parse_datetime(response)
        if start is None:
            self.logger.warning(f"Missing date, skipping: {response.url}")
            return

        title = self._parse_title(response)
        meeting = Meeting(
            title=title,
            description="",
            classification=COMMITTEE if "committee" in title.lower() else BOARD,
            start=start,
            end=end,
            all_day=all_day,
            time_notes="",
            location=self._parse_location(response),
            links=self._parse_links(response),
            source=response.url,
        )

        meeting["status"] = self._get_status(meeting)
        meeting["id"] = self._get_id(meeting)

        yield meeting

    def _parse_title(self, item):
        item_str = item.css("h1.page-header--xl::text").get()
        return " ".join(item_str.split()) if item_str else "Regular Meeting"

    def _first_li(self, response, icon):
        """First event-card <li> flagged by a Font Awesome icon class."""
        return response.xpath(f'(//li[.//span[contains(@class, "{icon}")]])[1]')

    def _parse_datetime(self, item) -> tuple[datetime, datetime, bool]:
        date_str = self._first_li(item, "fa-calendar").xpath(".//strong/text()").get()

        if not date_str:
            self.logger.warning(f"Missing date for item: {item.get()}")
            return None, None, False

        base = date_parser(date_str)

        time_str = " ".join(
            (
                self._first_li(item, "fa-clock").xpath(".//strong/text()").get() or ""
            ).split()
        )

        if not time_str or time_str.lower() == "all day":
            return base, None, True

        start_time_str, _, end_time_str = time_str.partition(" to ")

        start_dt = date_parser(f"{date_str} {start_time_str.strip()}")
        end_dt = date_parser(f"{date_str} {end_time_str.strip()}")

        return start_dt, end_dt, False

    def _parse_location(self, response):
        location_str = self._first_li(response, "fa-map-marker-alt")

        parts = [
            t.strip() for t in location_str.xpath(".//text()").getall() if t.strip()
        ]

        return {
            "name": parts[0] if parts else "",
            "address": " ".join(parts[1:]) if len(parts) > 1 else "",
        }

    def _parse_links(self, response):
        links = [
            {
                "href": response.url,
                "title": "Meeting Details",
            }
        ]
        seen = set()
        for a in response.css("div.col-md-7 a"):
            href = a.attrib.get("href", "")
            if not href or href in seen:
                continue
            title = " ".join(a.css("::text").getall()).strip()
            if href.lower().endswith(".pdf"):
                seen.add(href)
                links.append(
                    {"href": response.urljoin(href), "title": title or "Agenda"}
                )
            elif self.video_param in href:
                seen.add(href)
                links.append(
                    {"href": response.urljoin(href), "title": title.title() or "Video"}
                )
        return links
