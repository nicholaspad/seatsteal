from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_config import TermConfig


class USCScraper(BaseScraper):
    """
    University of Southern California course scraper.

    Scrapes course data from USC's Schedule of Classes.
    """

    BASE_URL = "https://classes.usc.edu"

    def __init__(self):
        super().__init__("usc")
        self.current_term = TermConfig.get_current_term("usc")

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape USC courses for a specific department.

        Args:
            department: Department code (e.g., 'CSCI', 'MATH', 'ENGL')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping USC {department} courses (limit: {limit}, term: {self.current_term})"
        )

        try:
            # USC schedule URL format
            url = f"{self.BASE_URL}/term-{self.current_term}/classes/{department}"
            soup = self.fetch_html(url)

            courses = []
            course_elements = soup.select(".course-info, .course-details")

            if not course_elements:
                logger.warning(f"No courses found for USC {department}")
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

            logger.info(f"Scraped {len(courses)} courses from USC {department}")
            return courses

        except Exception as e:
            logger.error(f"Failed to scrape USC {department}: {e}")
            raise

    def _parse_course(self, course_elem) -> Optional[Dict[str, Any]]:
        """Parse a single course element"""
        try:
            # Extract course code
            code_elem = course_elem.select_one(".course-id, .course-code")
            if not code_elem:
                return None
            course_code = code_elem.text.strip()

            # Extract title
            title_elem = course_elem.select_one(".course-title, .course-name")
            title = title_elem.text.strip() if title_elem else "Unknown"

            # Extract sections
            classes = []
            section_elements = course_elem.select(".section-info, .section-row")

            # Sometimes sections are in a sibling container
            if not section_elements:
                parent = course_elem.parent
                if parent:
                    section_elements = parent.select(".section-info, .section-row")

            for section_elem in section_elements:
                class_data = self._parse_class(section_elem)
                if class_data:
                    classes.append(class_data)

            return {"course_code": course_code, "title": title, "classes": classes}

        except Exception as e:
            logger.error(f"Error parsing course element: {e}")
            return None

    def _parse_class(self, section_elem) -> Optional[Dict[str, Any]]:
        """Parse a single class/section element"""
        try:
            # Extract section ID (USC's class number)
            section_id_elem = section_elem.select_one(".section-id, .section-number")
            class_number = section_id_elem.text.strip() if section_id_elem else ""

            # Extract section type (LEC, LAB, etc.) and number
            type_elem = section_elem.select_one(".section-type")
            section_code = type_elem.text.strip() if type_elem else ""

            # Status
            status_elem = section_elem.select_one(".status, .section-status")
            if status_elem:
                status = self.normalize_status(status_elem.text)
            else:
                status = "Unknown"

            return {
                "class_number": class_number,
                "section": section_code,
                "status": status,
            }

        except Exception as e:
            logger.error(f"Error parsing class element: {e}")
            return None
