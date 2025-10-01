from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_config import TermConfig


class PrincetonScraper(BaseScraper):
    """
    Princeton University course scraper.

    Scrapes course data from Princeton's registrar website.
    """

    BASE_URL = "https://registrar.princeton.edu/course-offerings"

    def __init__(self):
        super().__init__("princeton")
        self.current_term = TermConfig.get_current_term("princeton")

    async def scrape_courses(self, department: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape Princeton courses for a specific department.

        Args:
            department: Department code (e.g., 'COS', 'MAT', 'ENG')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(f"Scraping Princeton {department} courses (limit: {limit}, term: {self.current_term})")

        try:
            # Build URL for department
            url = f"{self.BASE_URL}?term={self.current_term}&subject={department}"
            soup = self.fetch_html(url)

            courses = []
            course_elements = soup.select(".course-item, .course")

            if not course_elements:
                logger.warning(f"No courses found for Princeton {department}")
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

            logger.info(f"Scraped {len(courses)} courses from Princeton {department}")
            return courses

        except Exception as e:
            logger.error(f"Failed to scrape Princeton {department}: {e}")
            raise

    def _parse_course(self, course_elem) -> Optional[Dict[str, Any]]:
        """Parse a single course element"""
        try:
            # Extract course code and title
            course_code_elem = course_elem.select_one(".course-code, .courseNumber")
            title_elem = course_elem.select_one(".course-title, .courseTitle")

            if not course_code_elem or not title_elem:
                return None

            course_code = course_code_elem.text.strip()
            title = title_elem.text.strip()

            # Extract classes/sections
            classes = []
            section_elements = course_elem.select(".section-item, .classSection")

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
            class_number_elem = section_elem.select_one(".class-number, [data-class-number]")
            class_number = (
                class_number_elem.get('data-class-number', '')
                if class_number_elem
                else section_elem.get('data-class-number', '')
            )

            # Extract section code
            section_code_elem = section_elem.select_one(".section-code, .section")
            section_code = section_code_elem.text.strip() if section_code_elem else ''

            # Extract instructor
            instructor_elem = section_elem.select_one(".instructor, .instructors")
            instructor = instructor_elem.text.strip() if instructor_elem else ''

            # Extract schedule
            schedule_elem = section_elem.select_one(".schedule, .meeting-times")
            schedule = schedule_elem.text.strip() if schedule_elem else ''

            # Extract location
            location_elem = section_elem.select_one(".location, .room")
            location = location_elem.text.strip() if location_elem else ''

            # Extract enrollment data
            enrolled_elem = section_elem.select_one(".enrolled, [data-enrolled]")
            capacity_elem = section_elem.select_one(".capacity, [data-capacity]")
            waitlist_elem = section_elem.select_one(".waitlist, [data-waitlist]")

            enrolled = int(enrolled_elem.get('data-enrolled', '0') if enrolled_elem else '0')
            capacity = int(capacity_elem.get('data-capacity', '0') if capacity_elem else '0')
            waitlist = int(waitlist_elem.get('data-waitlist', '0') if waitlist_elem else '0')

            # Extract status
            status_elem = section_elem.select_one(".status, .enrollment-status")
            status_text = status_elem.text.strip() if status_elem else 'Unknown'
            status = self.normalize_status(status_text)

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
