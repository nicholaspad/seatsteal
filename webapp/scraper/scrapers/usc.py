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

            # Instructor
            instructor_elem = section_elem.select_one(".instructor, .instructor-name")
            instructor = instructor_elem.text.strip() if instructor_elem else ""

            # Schedule/Days and Times
            days_elem = section_elem.select_one(".days")
            time_elem = section_elem.select_one(".time, .meeting-time")
            days = days_elem.text.strip() if days_elem else ""
            times = time_elem.text.strip() if time_elem else ""
            schedule = f"{days} {times}".strip() if days or times else ""

            # Location
            location_elem = section_elem.select_one(".location, .building-room")
            location = location_elem.text.strip() if location_elem else ""

            # Enrollment information
            registered_elem = section_elem.select_one(".registered, .enrolled")
            spaces_elem = section_elem.select_one(".spaces, .capacity")

            if registered_elem and spaces_elem:
                enrolled_text = registered_elem.text.strip()
                capacity_text = spaces_elem.text.strip()
                enrolled, capacity = self.parse_enrollment(enrolled_text, capacity_text)
            else:
                # Sometimes USC shows it as "X of Y"
                enrollment_elem = section_elem.select_one(".enrollment")
                if enrollment_elem:
                    enrollment_text = enrollment_elem.text.strip()
                    if " of " in enrollment_text:
                        parts = enrollment_text.split(" of ")
                        enrolled, capacity = self.parse_enrollment(parts[0], parts[1])
                    else:
                        enrolled, capacity = 0, 0
                else:
                    enrolled, capacity = 0, 0

            # Waitlist
            waitlist_elem = section_elem.select_one(".waitlist")
            waitlist = self.parse_waitlist(waitlist_elem.text) if waitlist_elem else 0

            # Status
            status_elem = section_elem.select_one(".status, .section-status")
            if status_elem:
                status_text = status_elem.text.strip()
                # USC uses specific status indicators
                if "open" in status_text.lower() or "available" in status_text.lower():
                    status = "Open"
                elif "closed" in status_text.lower() or "full" in status_text.lower():
                    status = "Closed"
                elif "waitlist" in status_text.lower():
                    status = "Waitlist"
                else:
                    status = self.normalize_status(status_text)
            elif enrolled >= capacity and capacity > 0:
                status = "Closed"
            elif waitlist > 0:
                status = "Waitlist"
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
                "waitlist": waitlist,
                "status": status,
            }

        except Exception as e:
            logger.error(f"Error parsing class element: {e}")
            return None
