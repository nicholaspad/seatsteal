from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from loguru import logger
import time


class BaseScraper(ABC):
    """Base class for all college course scrapers"""

    def __init__(self, college_short_name: str):
        """
        Initialize the scraper for a specific college.

        Args:
            college_short_name: Short identifier for the college (e.g., 'princeton', 'brown')
        """
        self.college_short_name = college_short_name
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        self.request_count = 0
        self.last_request_time = 0

    @abstractmethod
    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape courses for a specific department.

        This method must be implemented by each college scraper.

        Args:
            department: Department code (e.g., 'CS', 'MATH', 'ENG')
            limit: Optional limit on number of courses to scrape

        Returns:
            List of course dictionaries with the following structure:
            [
                {
                    'course_code': 'CS 101',
                    'title': 'Introduction to Computer Science',
                    'classes': [
                        {
                            'class_number': '12345',
                            'section': 'LEC 001',
                            'instructor': 'John Doe',
                            'schedule': 'MWF 10:00-11:00',
                            'location': 'Building 123',
                            'enrolled': 50,
                            'capacity': 100,
                            'waitlist': 5,
                            'status': 'Open'
                        },
                        ...
                    ]
                },
                ...
            ]
        """
        pass

    def fetch_html(self, url: str, timeout: int = 30) -> BeautifulSoup:
        """
        Fetch and parse HTML from a URL.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            BeautifulSoup object with parsed HTML

        Raises:
            requests.RequestException: If request fails
        """
        try:
            # Rate limiting: ensure minimum 100ms between requests
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            if time_since_last_request < 0.1:
                time.sleep(0.1 - time_since_last_request)

            logger.debug(f"Fetching {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            self.request_count += 1
            self.last_request_time = time.time()

            return BeautifulSoup(response.content, "lxml")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise

    def fetch_json(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Fetch JSON data from a URL.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON as dictionary

        Raises:
            requests.RequestException: If request fails
        """
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            if time_since_last_request < 0.1:
                time.sleep(0.1 - time_since_last_request)

            logger.debug(f"Fetching JSON from {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            self.request_count += 1
            self.last_request_time = time.time()

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Failed to fetch JSON from {url}: {e}")
            raise

    def parse_enrollment(
        self, enrolled_text: str, capacity_text: str
    ) -> tuple[int, int]:
        """
        Parse enrollment numbers from text strings.

        Args:
            enrolled_text: Text containing enrolled count
            capacity_text: Text containing capacity

        Returns:
            Tuple of (enrolled, capacity) as integers
        """
        try:
            # Remove common non-numeric characters
            enrolled_clean = "".join(filter(str.isdigit, enrolled_text.strip()))
            capacity_clean = "".join(filter(str.isdigit, capacity_text.strip()))

            enrolled = int(enrolled_clean) if enrolled_clean else 0
            capacity = int(capacity_clean) if capacity_clean else 0

            return enrolled, capacity

        except (ValueError, AttributeError) as e:
            logger.warning(
                f"Failed to parse enrollment: enrolled='{enrolled_text}', capacity='{capacity_text}': {e}"
            )
            return 0, 0

    def parse_waitlist(self, waitlist_text: str) -> int:
        """
        Parse waitlist number from text.

        Args:
            waitlist_text: Text containing waitlist count

        Returns:
            Waitlist count as integer
        """
        try:
            waitlist_clean = "".join(filter(str.isdigit, waitlist_text.strip()))
            return int(waitlist_clean) if waitlist_clean else 0
        except (ValueError, AttributeError):
            return 0

    def normalize_status(self, status_text: str) -> str:
        """
        Normalize status text to standard values.

        Args:
            status_text: Raw status text from website

        Returns:
            Normalized status: 'Open', 'Closed', 'Waitlist', or 'Unknown'
        """
        status_lower = status_text.lower().strip()

        if "open" in status_lower or "available" in status_lower:
            return "Open"
        elif (
            "closed" in status_lower
            or "full" in status_lower
            or "filled" in status_lower
        ):
            return "Closed"
        elif "waitlist" in status_lower or "wait list" in status_lower:
            return "Waitlist"
        else:
            return "Unknown"

    def close(self):
        """Close the HTTP session"""
        self.session.close()
        logger.debug(f"Scraper closed. Total requests: {self.request_count}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
