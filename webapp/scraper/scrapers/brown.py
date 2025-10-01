from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re
from ..base import BaseScraper
from ..utils.logger import scraper_logger as logger
from ..utils.term_config import TermConfig


class BrownScraper(BaseScraper):
    """
    Brown University course scraper.

    Scrapes course data from Brown's Courses@Brown system (CAB).
    """

    BASE_URL = "https://cab.brown.edu"

    def __init__(self):
        super().__init__("brown")
        self.current_term = TermConfig.get_current_term("brown")

    async def scrape_courses(self, department: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape Brown courses for a specific department.

        Args:
            department: Department code (e.g., 'CSCI', 'MATH', 'ENGL')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(f"Scraping Brown {department} courses (limit: {limit}, term: {self.current_term})")

        try:
            # Brown often uses an API or specific search endpoints
            url = f"{self.BASE_URL}/api/?page=fose&route=search"

            # For this implementation, we'll use HTML scraping
            # In a real scenario, you might need to make POST requests with search parameters
            search_url = f"{self.BASE_URL}/public/search?term={self.current_term}&dept={department}"
            soup = self.fetch_html(search_url)

            courses = []
            course_elements = soup.select(".result--group-start, .course-result")

            if not course_elements:
                logger.warning(f"No courses found for Brown {department}")
                return []

            for idx, course_elem in enumerate(course_elements):
                if limit and idx >= limit:
                    break

                try:
                    course_data = self._parse_course(course_elem)
                    if course_data:
                        courses.append(course_data)
                except Exception as e:
                    logger.error(f"Failed to parse course: {e}")
                    continue

            logger.info(f"Scraped {len(courses)} courses from Brown {department}")
            return courses

        except Exception as e:
            logger.error(f"Failed to scrape Brown {department}: {e}")
            raise

    def _parse_course(self, course_elem) -> Optional[Dict[str, Any]]:
        """Parse a single course element"""
        try:
            # Extract course code
            code_elem = course_elem.select_one(".course-code, .result__code")
            if not code_elem:
                return None
            course_code = code_elem.text.strip()

            # Extract title
            title_elem = course_elem.select_one(".course-title, .result__title")
            title = title_elem.text.strip() if title_elem else "Unknown"

            # Extract sections
            classes = []
            section_elements = course_elem.select(".section, .result__section")

            for section_elem in section_elements:
                class_data = self._parse_class(section_elem)
                if class_data:
                    classes.append(class_data)

            return {
                'course_code': course_code,
                'title': title,
                'classes': classes
            }

        except Exception as e:
            logger.error(f"Error parsing course element: {e}")
            return None

    def _parse_class(self, section_elem) -> Optional[Dict[str, Any]]:
        """Parse a single class/section element"""
        try:
            # Extract CRN (Course Reference Number) - Brown's class identifier
            crn_elem = section_elem.select_one(".crn, [data-crn]")
            class_number = crn_elem.text.strip() if crn_elem else section_elem.get('data-crn', '')

            # Extract section code
            section_elem_code = section_elem.select_one(".section-code, .section-num")
            section_code = section_elem_code.text.strip() if section_elem_code else ''

            # Extract instructor
            instructor_elem = section_elem.select_one(".instructor, .faculty")
            instructor = instructor_elem.text.strip() if instructor_elem else ''

            # Extract meeting times
            time_elem = section_elem.select_one(".time, .meeting-time")
            schedule = time_elem.text.strip() if time_elem else ''

            # Extract location
            location_elem = section_elem.select_one(".location, .building-room")
            location = location_elem.text.strip() if location_elem else ''

            # Extract enrollment
            enrolled_elem = section_elem.select_one(".enrolled, .seats-taken")
            capacity_elem = section_elem.select_one(".capacity, .seats-total")

            enrolled_text = enrolled_elem.text if enrolled_elem else '0'
            capacity_text = capacity_elem.text if capacity_elem else '0'
            enrolled, capacity = self.parse_enrollment(enrolled_text, capacity_text)

            # Extract waitlist
            waitlist_elem = section_elem.select_one(".waitlist")
            waitlist = self.parse_waitlist(waitlist_elem.text) if waitlist_elem else 0

            # Determine status
            status_elem = section_elem.select_one(".status, .availability")
            if status_elem:
                status = self.normalize_status(status_elem.text)
            elif enrolled >= capacity:
                status = 'Closed'
            else:
                status = 'Open'

            return {
                'class_number': class_number,
                'section': section_code,
                'instructor': instructor,
                'schedule': schedule,
                'location': location,
                'enrolled': enrolled,
                'capacity': capacity,
                'waitlist': waitlist,
                'status': status
            }

        except Exception as e:
            logger.error(f"Error parsing class element: {e}")
            return None
