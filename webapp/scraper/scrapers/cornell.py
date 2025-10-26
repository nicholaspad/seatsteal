from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re
from scraper.base import BaseScraper
from scraper.utils.logger import scraper_logger as logger
from scraper.utils.term_config import TermConfig


class CornellScraper(BaseScraper):
    """
    Cornell University course scraper.

    Scrapes course data from Cornell's Class Roster.
    """

    BASE_URL = "https://classes.cornell.edu/browse/roster"

    def __init__(self):
        super().__init__("cornell")
        self.current_term = TermConfig.get_current_term("cornell")

    async def scrape_courses(
        self, department: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape Cornell courses for a specific department or all departments.

        Args:
            department: Department code (e.g., 'CS', 'MATH', 'ENGL') or 'ALL' for all subjects
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries with class information
        """
        logger.info(
            f"Scraping Cornell {department} courses (limit: {limit}, term: {self.current_term})"
        )

        try:
            # Handle "ALL" case - scrape all subjects
            if department.upper() == "ALL":
                return await self._scrape_all_subjects(limit)

            # Scrape single subject
            return await self._scrape_single_subject(department, limit)

        except Exception as e:
            logger.error(f"Failed to scrape Cornell {department}: {e}")
            raise

    async def _scrape_all_subjects(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape all subjects from Cornell's course roster.

        Args:
            limit: Optional limit on number of courses per subject

        Returns:
            List of all course dictionaries across all subjects
        """
        logger.info("Scraping all Cornell subjects")

        # Load base roster page to get all subjects
        base_url = f"{self.BASE_URL}/{self.current_term}"
        soup = self.fetch_html(base_url)

        # Extract all subjects from the browse page
        subjects = []
        subject_groups = soup.select(".subject-group")

        for group in subject_groups:
            code_elem = group.select_one(".browse-subjectcode a")
            name_elem = group.select_one(".browse-subjectdescr a")

            if code_elem and name_elem:
                code = code_elem.text.strip()
                name = name_elem.text.strip()
                if code and name:
                    subjects.append({"code": code, "name": name})

        logger.info(f"Found {len(subjects)} subjects to scrape")

        if not subjects:
            logger.warning("No subjects found on browse page")
            return []

        # Scrape each subject
        all_courses = []
        for subject in subjects:
            try:
                logger.info(f"Scraping subject {subject['code']} ({subject['name']})")
                courses = await self._scrape_single_subject(subject["code"], limit)
                all_courses.extend(courses)
                logger.info(f"Found {len(courses)} courses for {subject['code']}")
            except Exception as e:
                logger.error(f"Failed to scrape subject {subject['code']}: {e}")
                continue

        logger.info(f"Scraped total of {len(all_courses)} courses from all subjects")
        return all_courses

    async def _scrape_single_subject(
        self, subject_code: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape courses for a single subject.

        Args:
            subject_code: Subject code (e.g., 'CS', 'AAP')
            limit: Optional limit on number of courses

        Returns:
            List of course dictionaries
        """
        # Cornell roster URL format
        url = f"{self.BASE_URL}/{self.current_term}/subject/{subject_code}"
        soup = self.fetch_html(url)

        courses = []
        course_elements = soup.select(".node")

        if not course_elements:
            logger.warning(f"No courses found for Cornell {subject_code}")
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

        logger.info(f"Scraped {len(courses)} courses from Cornell {subject_code}")
        return courses

    def _parse_course(self, course_elem) -> Optional[Dict[str, Any]]:
        """Parse a single course element"""
        try:
            # Extract course title link (contains course code and title)
            title_link = course_elem.select_one('a[id*="dtitle"]')
            if not title_link:
                return None

            # Parse course code and title from aria-label
            # Format: "AAP 1100 - The Worlds We Make"
            aria_label = title_link.get("aria-label", "")
            if not aria_label:
                # Fallback to link text
                aria_label = title_link.text.strip()

            # Parse course code and title using regex
            match = re.match(r"^([A-Z]+\s*\d+[A-Z]*)\s*-\s*(.+)$", aria_label)
            if match:
                course_code = match.group(1).replace("  ", " ").strip()
                title = match.group(2).strip()
            else:
                # Fallback parsing
                course_code = (
                    aria_label.split("-")[0].strip()
                    if "-" in aria_label
                    else aria_label
                )
                title = (
                    aria_label.split("-", 1)[1].strip()
                    if "-" in aria_label
                    else aria_label
                )

            # Extract classes from class-numbers sections
            classes = []
            class_sections = course_elem.select(".class-numbers")

            for class_section in class_sections:
                class_data = self._parse_class(class_section)
                if class_data:
                    classes.append(class_data)

            # If no classes found, still return the course (might be informational)
            return {"course_code": course_code, "title": title, "classes": classes}

        except Exception as e:
            logger.error(f"Error parsing course element: {e}")
            return None

    def _parse_class(self, section_elem) -> Optional[Dict[str, Any]]:
        """Parse a single class/section element from .class-numbers structure"""
        try:
            # Extract class number from <strong> element
            strong_elem = section_elem.select_one('strong[title="Class Number"]')
            class_number = (
                strong_elem.text.strip().replace(" ", "") if strong_elem else None
            )

            if not class_number:
                return None

            # Extract section code from <em> element and following text
            # Format: "<em>LEC</em> 001"
            em_elem = section_elem.select_one('em[title="Component"]')
            section_code = "001"  # Default

            if em_elem:
                section_type = em_elem.text.strip()

                # Get the text that follows the <em> element
                parent_text = section_elem.get_text()
                em_text = em_elem.text

                # Find section number after the component type
                after_em_idx = parent_text.find(em_text)
                if after_em_idx != -1:
                    after_em_text = parent_text[after_em_idx + len(em_text) :]
                    # Look for digits
                    number_match = re.search(r"(\d+)", after_em_text)
                    if number_match:
                        section_number = number_match.group(1)
                        section_code = f"{section_type} {section_number}"
                    else:
                        section_code = section_type

            # For Cornell, we get minimal data from .class-numbers
            # Additional details would need to be extracted from other parts of the page
            # Set defaults for now
            return {
                "class_number": class_number,
                "section": section_code,
                "instructor": "",  # Would need to extract from different section
                "schedule": "",  # Would need to extract from different section
                "location": "",  # Would need to extract from different section
                "enrolled": 0,  # Would need to extract from enrollment section
                "capacity": 0,  # Would need to extract from enrollment section
                "waitlist": 0,  # Would need to extract from enrollment section
                "status": "Unknown",  # Would need to extract from status indicators
            }

        except Exception as e:
            logger.error(f"Error parsing class element: {e}")
            return None
