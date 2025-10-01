from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ..base import BaseScraper
from ..utils.logger import scraper_logger as logger
from ..utils.term_config import TermConfig


class CornellScraper(BaseScraper):
    """
    Cornell University course scraper.

    Scrapes course data from Cornell's Class Roster.
    """

    BASE_URL = "https://classes.cornell.edu/browse/roster"

    def __init__(self):
        super().__init__("cornell")
        self.current_term = TermConfig.get_current_term("cornell")

    async def scrape_courses(self, department: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape Cornell courses for a specific department.

        Args:
            department: Department code (e.g., 'CS', 'MATH', 'ENGL')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(f"Scraping Cornell {department} courses (limit: {limit}, term: {self.current_term})")

        try:
            # Cornell roster URL format
            url = f"{self.BASE_URL}/{self.current_term}/subject/{department}"
            soup = self.fetch_html(url)

            courses = []
            course_elements = soup.select(".node-class, .class-roster-node")

            if not course_elements:
                logger.warning(f"No courses found for Cornell {department}")
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

            logger.info(f"Scraped {len(courses)} courses from Cornell {department}")
            return courses

        except Exception as e:
            logger.error(f"Failed to scrape Cornell {department}: {e}")
            raise

    def _parse_course(self, course_elem) -> Optional[Dict[str, Any]]:
        """Parse a single course element"""
        try:
            # Extract course number and title
            title_elem = course_elem.select_one(".title, .title-coursedescr")
            if not title_elem:
                return None

            full_title = title_elem.text.strip()
            # Format: "CS 2110: Object-Oriented Programming"
            parts = full_title.split(':', 1)
            course_code = parts[0].strip() if len(parts) > 0 else "Unknown"
            title = parts[1].strip() if len(parts) > 1 else full_title

            # Extract sections
            classes = []
            section_elements = course_elem.select(".section, .class-section")

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
            # Extract class number
            class_num_elem = section_elem.select_one(".classNbr, .class-number")
            class_number = class_num_elem.text.strip() if class_num_elem else ''

            # Section type and number
            section_elem_type = section_elem.select_one(".section-type, .component-long")
            section_code = section_elem_type.text.strip() if section_elem_type else ''

            # Instructor
            instructor_elem = section_elem.select_one(".instructors, .instructor-detail")
            instructor = instructor_elem.text.strip() if instructor_elem else ''

            # Meeting patterns (schedule)
            pattern_elem = section_elem.select_one(".pattern-detail, .meeting-pattern")
            schedule = pattern_elem.text.strip() if pattern_elem else ''

            # Location
            location_elem = section_elem.select_one(".facility-detail, .location")
            location = location_elem.text.strip() if location_elem else ''

            # Enrollment
            enrolled_elem = section_elem.select_one(".enrolled-count, .enroll-total")
            capacity_elem = section_elem.select_one(".class-size, .enroll-max")
            waitlist_elem = section_elem.select_one(".waitlist-count, .wait-total")

            enrolled_text = enrolled_elem.text if enrolled_elem else '0'
            capacity_text = capacity_elem.text if capacity_elem else '0'
            enrolled, capacity = self.parse_enrollment(enrolled_text, capacity_text)
            waitlist = self.parse_waitlist(waitlist_elem.text) if waitlist_elem else 0

            # Status
            status_elem = section_elem.select_one(".status, .open-status")
            if status_elem:
                status = self.normalize_status(status_elem.text)
            elif enrolled >= capacity and capacity > 0:
                status = 'Closed'
            elif waitlist > 0:
                status = 'Waitlist'
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
