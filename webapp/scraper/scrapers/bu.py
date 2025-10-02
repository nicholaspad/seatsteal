from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_config import TermConfig


class BUScraper(BaseScraper):
    """
    Boston University course scraper.

    Scrapes course data from BU's course schedule website.
    """

    BASE_URL = "https://www.bu.edu/phpbin/course-search"

    def __init__(self):
        super().__init__("bu")
        self.current_term = TermConfig.get_current_term("bu")

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape BU courses for a specific department.

        Args:
            department: Department code (e.g., 'CAS CS', 'CAS MA', 'ENG')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping BU {department} courses (limit: {limit}, term: {self.current_term})"
        )

        try:
            # BU uses a search form - construct URL
            url = f"{self.BASE_URL}/index.html"
            params = {
                "term": self.current_term,
                "search": "Search",
                "college": department.split()[0] if " " in department else department,
                "dept": department.split()[1] if " " in department else department,
            }

            # Fetch with params
            soup = self.fetch_html(
                f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
            )

            courses = []
            course_elements = soup.select(".course-listing, .course-feed")

            if not course_elements:
                logger.warning(f"No courses found for BU {department}")
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

            logger.info(f"Scraped {len(courses)} courses from BU {department}")
            return courses

        except Exception as e:
            logger.error(f"Failed to scrape BU {department}: {e}")
            raise

    def _parse_course(self, course_elem) -> Optional[Dict[str, Any]]:
        """Parse a single course element"""
        try:
            # Extract course info
            course_title_elem = course_elem.select_one(".course-title, h3")
            if not course_title_elem:
                return None

            full_title = course_title_elem.text.strip()
            # BU typically has format: "CAS CS 111: Introduction to Programming"
            parts = full_title.split(":", 1)
            course_code = parts[0].strip() if len(parts) > 0 else "Unknown"
            title = parts[1].strip() if len(parts) > 1 else full_title

            # Extract sections
            classes = []
            section_elements = course_elem.select(".section-data, .course-section")

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
            # Extract section number
            section_num_elem = section_elem.select_one(".section-number, .sec")
            section_code = section_num_elem.text.strip() if section_num_elem else ""

            # Class number
            class_num_elem = section_elem.select_one(".class-number, .courseNumber")
            class_number = class_num_elem.text.strip() if class_num_elem else ""

            # Instructor
            instructor_elem = section_elem.select_one(".instructor, .faculty-name")
            instructor = instructor_elem.text.strip() if instructor_elem else ""

            # Schedule
            schedule_elem = section_elem.select_one(".schedule, .meeting-time")
            schedule = schedule_elem.text.strip() if schedule_elem else ""

            # Location
            location_elem = section_elem.select_one(".location, .room")
            location = location_elem.text.strip() if location_elem else ""

            # Enrollment
            enrollment_elem = section_elem.select_one(".enrollment, .seats")
            if enrollment_elem:
                enrollment_text = enrollment_elem.text.strip()
                # BU typically shows "X of Y" format
                if "/" in enrollment_text or " of " in enrollment_text:
                    parts = enrollment_text.replace(" of ", "/").split("/")
                    enrolled, capacity = self.parse_enrollment(parts[0], parts[1])
                else:
                    enrolled, capacity = 0, 0
            else:
                enrolled, capacity = 0, 0

            # Status
            status_elem = section_elem.select_one(".status, .availability")
            if status_elem:
                status = self.normalize_status(status_elem.text)
            elif enrolled >= capacity and capacity > 0:
                status = "Closed"
            else:
                status = "Open"

            return {
                "class_number": class_number,
                "section": section_code,
                "instructor": instructor,
                "schedule": schedule,
                "location": location,
                "enrolled": enrolled,
                "capacity": capacity,
                "waitlist": 0,
                "status": status,
            }

        except Exception as e:
            logger.error(f"Error parsing class element: {e}")
            return None
