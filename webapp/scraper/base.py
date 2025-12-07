from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
import asyncio
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
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "SeatSteal/1.0",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate, br",
            },
            timeout=30.0,
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
                            'status': 'Open'
                        },
                        ...
                    ]
                },
                ...
            ]
        """
        pass

    async def fetch_html(self, url: str, timeout: int = 30) -> BeautifulSoup:
        """
        Fetch and parse HTML from a URL.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            BeautifulSoup object with parsed HTML

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            # Rate limiting: ensure minimum 100ms between requests
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            if time_since_last_request < 0.1:
                await asyncio.sleep(0.1 - time_since_last_request)

            logger.debug(f"Fetching {url}")
            response = await self.client.get(url, timeout=timeout)
            response.raise_for_status()
            self.request_count += 1
            self.last_request_time = time.time()

            return BeautifulSoup(response.content, "lxml")

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise

    async def fetch_json(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Fetch JSON data from a URL.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON as dictionary

        Raises:
            httpx.HTTPError: If request fails
        """
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            if time_since_last_request < 0.1:
                await asyncio.sleep(0.1 - time_since_last_request)

            logger.debug(f"Fetching JSON from {url}")
            response = await self.client.get(url, timeout=timeout)
            response.raise_for_status()
            self.request_count += 1
            self.last_request_time = time.time()

            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch JSON from {url}: {e}")
            raise

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

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        logger.debug(f"Scraper closed. Total requests: {self.request_count}")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
