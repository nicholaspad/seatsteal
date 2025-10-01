from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ..base import BaseScraper
from ..utils.logger import scraper_logger as logger
from ..utils.term_config import TermConfig


class NEUScraper(BaseScraper):
    """
    Northeastern University course scraper.

    Scrapes course data from Northeastern's Banner system.
    """

    BASE_URL = "https://nubanner.neu.edu/StudentRegistrationSsb/ssb"

    def __init__(self):
        super().__init__("neu")
        self.current_term = TermConfig.get_current_term("neu")

    async def scrape_courses(self, department: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape NEU courses for a specific department.

        Args:
            department: Department code (e.g., 'CS', 'MATH', 'ENGL')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(f"Scraping NEU {department} courses (limit: {limit}, term: {self.current_term})")

        try:
            # NEU often uses an API endpoint for course search
            # This is a simplified version - real implementation would use the API
            search_url = f"{self.BASE_URL}/searchResults/searchResults"
            params = {
                'term': self.current_term,
                'subject': department,
                'txt_subject': department,
            }

            # Try to fetch as JSON first (NEU uses JSON API)
            try:
                data = self.fetch_json(f"{search_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}")
                courses = self._parse_json_response(data, limit)
            except Exception:
                # Fall back to HTML scraping
                soup = self.fetch_html(f"{search_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}")
                courses = self._parse_html_response(soup, limit)

            logger.info(f"Scraped {len(courses)} courses from NEU {department}")
            return courses

        except Exception as e:
            logger.error(f"Failed to scrape NEU {department}: {e}")
            raise

    def _parse_json_response(self, data: Dict, limit: Optional[int]) -> List[Dict[str, Any]]:
        """Parse JSON API response"""
        courses = []
        course_data_list = data.get('data', []) if isinstance(data, dict) else []

        for idx, course_data in enumerate(course_data_list):
            if limit and idx >= limit:
                break

            try:
                course_code = course_data.get('subject', '') + ' ' + course_data.get('courseNumber', '')
                title = course_data.get('courseTitle', '')

                # Parse sections
                classes = []
                sections = course_data.get('sections', [])
                for section in sections:
                    class_info = {
                        'class_number': section.get('courseReferenceNumber', ''),
                        'section': section.get('sequenceNumber', ''),
                        'instructor': ', '.join([i.get('displayName', '') for i in section.get('faculty', [])]),
                        'schedule': self._format_meeting_times(section.get('meetingsFaculty', [])),
                        'location': self._format_location(section.get('meetingsFaculty', [])),
                        'enrolled': int(section.get('enrollment', 0)),
                        'capacity': int(section.get('maximumEnrollment', 0)),
                        'waitlist': int(section.get('waitCount', 0)),
                        'status': self.normalize_status(section.get('openSection', 'N') == 'Y' and 'Open' or 'Closed')
                    }
                    classes.append(class_info)

                courses.append({
                    'course_code': course_code.strip(),
                    'title': title,
                    'classes': classes
                })

            except Exception as e:
                logger.error(f"Failed to parse course from JSON: {e}")
                continue

        return courses

    def _parse_html_response(self, soup: BeautifulSoup, limit: Optional[int]) -> List[Dict[str, Any]]:
        """Parse HTML response as fallback"""
        courses = []
        course_elements = soup.select(".searchResultsItem, .course-row")

        for idx, course_elem in enumerate(course_elements):
            if limit and idx >= limit:
                break

            try:
                course_data = self._parse_course_html(course_elem)
                if course_data:
                    courses.append(course_data)
            except Exception as e:
                logger.error(f"Failed to parse course: {e}")
                continue

        return courses

    def _parse_course_html(self, course_elem) -> Optional[Dict[str, Any]]:
        """Parse course from HTML"""
        try:
            # Extract course code and title
            title_elem = course_elem.select_one(".course-title, h3")
            if not title_elem:
                return None

            full_text = title_elem.text.strip()
            parts = full_text.split(' - ', 1)
            course_code = parts[0].strip() if len(parts) > 0 else "Unknown"
            title = parts[1].strip() if len(parts) > 1 else full_text

            # Extract section info
            classes = []
            section_elem = course_elem.select_one(".section-details")
            if section_elem:
                class_data = self._parse_class_html(section_elem)
                if class_data:
                    classes.append(class_data)

            return {
                'course_code': course_code,
                'title': title,
                'classes': classes
            }

        except Exception as e:
            logger.error(f"Error parsing course HTML: {e}")
            return None

    def _parse_class_html(self, section_elem) -> Optional[Dict[str, Any]]:
        """Parse class/section from HTML"""
        try:
            crn_elem = section_elem.select_one(".crn, .class-number")
            class_number = crn_elem.text.strip() if crn_elem else ''

            section_elem_code = section_elem.select_one(".section-number")
            section_code = section_elem_code.text.strip() if section_elem_code else ''

            instructor_elem = section_elem.select_one(".instructor")
            instructor = instructor_elem.text.strip() if instructor_elem else ''

            schedule_elem = section_elem.select_one(".meeting-time")
            schedule = schedule_elem.text.strip() if schedule_elem else ''

            location_elem = section_elem.select_one(".location")
            location = location_elem.text.strip() if location_elem else ''

            enrolled_elem = section_elem.select_one(".enrolled")
            capacity_elem = section_elem.select_one(".capacity")
            enrolled, capacity = self.parse_enrollment(
                enrolled_elem.text if enrolled_elem else '0',
                capacity_elem.text if capacity_elem else '0'
            )

            status_elem = section_elem.select_one(".status")
            status = self.normalize_status(status_elem.text) if status_elem else 'Unknown'

            return {
                'class_number': class_number,
                'section': section_code,
                'instructor': instructor,
                'schedule': schedule,
                'location': location,
                'enrolled': enrolled,
                'capacity': capacity,
                'waitlist': 0,
                'status': status
            }

        except Exception as e:
            logger.error(f"Error parsing class HTML: {e}")
            return None

    def _format_meeting_times(self, meetings: List[Dict]) -> str:
        """Format meeting times from API data"""
        if not meetings:
            return ''

        times = []
        for meeting in meetings:
            meeting_time = meeting.get('meetingTime', {})
            days = meeting_time.get('meetingDays', '')
            start_time = meeting_time.get('beginTime', '')
            end_time = meeting_time.get('endTime', '')
            if days and start_time and end_time:
                times.append(f"{days} {start_time}-{end_time}")

        return ', '.join(times)

    def _format_location(self, meetings: List[Dict]) -> str:
        """Format location from API data"""
        if not meetings:
            return ''

        locations = []
        for meeting in meetings:
            building = meeting.get('building', '')
            room = meeting.get('room', '')
            if building or room:
                locations.append(f"{building} {room}".strip())

        return ', '.join(locations)
