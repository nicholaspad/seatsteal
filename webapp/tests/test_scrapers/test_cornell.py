"""Tests for Cornell University course scraper."""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup

import sys
from pathlib import Path

# Add webapp directory to path
webapp_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(webapp_dir))

from scraper.scrapers.cornell import CornellScraper
from models.college import College


# Sample Cornell HTML response data for a course listing
SAMPLE_CORNELL_COURSE_HTML = """
<div class="node">
    <a id="dtitle-123" aria-label="CS 1110 - Introduction to Computing Using Python">CS 1110</a>
    <div class="sections">
        <i class="fa fa-circle open-status-open"></i>
        <i class="fa fa-circle open-status-closed"></i>
        <div class="class-numbers">
            <strong title="Class Number">12345</strong>
            <em title="Component">LEC</em> 001
        </div>
        <div class="class-numbers">
            <strong title="Class Number">12346</strong>
            <em title="Component">LEC</em> 002
        </div>
    </div>
</div>
"""

SAMPLE_CORNELL_COURSE_HTML_OPEN = """
<div class="node">
    <a id="dtitle-456" aria-label="MATH 1920 - Multivariable Calculus">MATH 1920</a>
    <div class="sections">
        <i class="fa fa-circle open-status-open"></i>
        <div class="class-numbers">
            <strong title="Class Number">20001</strong>
            <em title="Component">LEC</em> 001
        </div>
    </div>
</div>
"""

# Sample Cornell browse page HTML for subject listing
SAMPLE_CORNELL_SUBJECTS_HTML = """
<html>
<body>
    <div class="subject-group">
        <div class="browse-subjectcode"><a>CS</a></div>
        <div class="browse-subjectdescr"><a>Computer Science</a></div>
    </div>
    <div class="subject-group">
        <div class="browse-subjectcode"><a>MATH</a></div>
        <div class="browse-subjectdescr"><a>Mathematics</a></div>
    </div>
</body>
</html>
"""

# Sample Cornell course list page HTML
SAMPLE_CORNELL_COURSE_LIST_HTML = f"""
<html>
<body>
    {SAMPLE_CORNELL_COURSE_HTML}
    {SAMPLE_CORNELL_COURSE_HTML_OPEN}
</body>
</html>
"""


@pytest.fixture
def mock_cornell_db_session():
    """Create a mock database session for Cornell scraper."""
    mock_session = MagicMock(spec=Session)
    mock_college = College(
        id=1,
        name="Cornell University",
        short_name="cornell",
        term_code="FA24",
        term_name="Fall 2024",
        is_active=True,
    )

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_college
    mock_session.execute.return_value = mock_result

    return mock_session


class TestCornellScraper:
    """Tests for CornellScraper class."""

    @pytest.mark.unit
    def test_init_sets_college_and_term(self, mock_cornell_db_session):
        """Test that scraper correctly initializes with college and term code."""
        scraper = CornellScraper(mock_cornell_db_session)

        assert scraper.college_short_name == "cornell"
        assert scraper.current_term == "FA24"

    @pytest.mark.unit
    def test_parse_class_extracts_data(self, mock_cornell_db_session):
        """Test parsing a single class section element."""
        scraper = CornellScraper(mock_cornell_db_session)

        html = """
        <div class="class-numbers">
            <strong title="Class Number">12345</strong>
            <em title="Component">LEC</em> 001
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        section_elem = soup.select_one(".class-numbers")

        result = scraper._parse_class(section_elem, "open")

        assert result is not None
        assert result["class_number"] == "12345"
        assert result["section"] == "LEC 001"
        assert result["status"] == "open"

    @pytest.mark.unit
    def test_parse_class_with_different_status(self, mock_cornell_db_session):
        """Test parsing class with closed status."""
        scraper = CornellScraper(mock_cornell_db_session)

        html = """
        <div class="class-numbers">
            <strong title="Class Number">99999</strong>
            <em title="Component">DIS</em> 003
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        section_elem = soup.select_one(".class-numbers")

        result = scraper._parse_class(section_elem, "closed")

        assert result is not None
        assert result["class_number"] == "99999"
        assert result["section"] == "DIS 003"
        assert result["status"] == "closed"

    @pytest.mark.unit
    def test_parse_class_missing_class_number(self, mock_cornell_db_session):
        """Test that class without class number returns None."""
        scraper = CornellScraper(mock_cornell_db_session)

        html = """
        <div class="class-numbers">
            <em title="Component">LEC</em> 001
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        section_elem = soup.select_one(".class-numbers")

        result = scraper._parse_class(section_elem, "open")

        assert result is None

    @pytest.mark.unit
    def test_parse_course_extracts_full_data(self, mock_cornell_db_session):
        """Test parsing a complete course element with multiple classes."""
        scraper = CornellScraper(mock_cornell_db_session)

        soup = BeautifulSoup(SAMPLE_CORNELL_COURSE_HTML, "html.parser")
        course_elem = soup.select_one(".node")

        result = scraper._parse_course(course_elem)

        assert result is not None
        assert result["course_code"] == "CS 1110"
        assert result["title"] == "Introduction to Computing Using Python"
        assert len(result["classes"]) == 2

        # Check first class (open)
        assert result["classes"][0]["class_number"] == "12345"
        assert result["classes"][0]["section"] == "LEC 001"
        assert result["classes"][0]["status"] == "open"

        # Check second class (closed)
        assert result["classes"][1]["class_number"] == "12346"
        assert result["classes"][1]["section"] == "LEC 002"
        assert result["classes"][1]["status"] == "closed"

    @pytest.mark.unit
    def test_parse_course_open_status(self, mock_cornell_db_session):
        """Test parsing course with open status."""
        scraper = CornellScraper(mock_cornell_db_session)

        soup = BeautifulSoup(SAMPLE_CORNELL_COURSE_HTML_OPEN, "html.parser")
        course_elem = soup.select_one(".node")

        result = scraper._parse_course(course_elem)

        assert result is not None
        assert result["course_code"] == "MATH 1920"
        assert result["title"] == "Multivariable Calculus"
        assert len(result["classes"]) == 1
        assert result["classes"][0]["status"] == "open"

    @pytest.mark.unit
    def test_parse_course_missing_title_link(self, mock_cornell_db_session):
        """Test that course without title link returns None."""
        scraper = CornellScraper(mock_cornell_db_session)

        html = """
        <div class="node">
            <div class="sections">
                <div class="class-numbers">
                    <strong title="Class Number">12345</strong>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        course_elem = soup.select_one(".node")

        result = scraper._parse_course(course_elem)

        assert result is None

    @pytest.mark.unit
    def test_parse_course_with_no_classes(self, mock_cornell_db_session):
        """Test parsing course with no class sections."""
        scraper = CornellScraper(mock_cornell_db_session)

        html = """
        <div class="node">
            <a id="dtitle-123" aria-label="CS 9999 - Special Topics">CS 9999</a>
            <div class="sections">
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        course_elem = soup.select_one(".node")

        result = scraper._parse_course(course_elem)

        # Course should still be returned even with no classes
        assert result is not None
        assert result["course_code"] == "CS 9999"
        assert result["title"] == "Special Topics"
        assert result["classes"] == []

    @pytest.mark.unit
    @patch("scraper.scrapers.cornell.CornellScraper.fetch_html")
    async def test_scrape_single_subject(
        self, mock_fetch_html, mock_cornell_db_session
    ):
        """Test scraping a single subject/department."""
        scraper = CornellScraper(mock_cornell_db_session)

        # Mock HTML response
        soup = BeautifulSoup(SAMPLE_CORNELL_COURSE_LIST_HTML, "html.parser")
        mock_fetch_html.return_value = soup

        result = await scraper._scrape_single_subject("CS")

        assert len(result) == 2
        assert result[0]["course_code"] == "CS 1110"
        assert result[1]["course_code"] == "MATH 1920"

    @pytest.mark.unit
    @patch("scraper.scrapers.cornell.CornellScraper.fetch_html")
    async def test_scrape_single_subject_with_limit(
        self, mock_fetch_html, mock_cornell_db_session
    ):
        """Test scraping with course limit."""
        scraper = CornellScraper(mock_cornell_db_session)

        # Mock HTML response
        soup = BeautifulSoup(SAMPLE_CORNELL_COURSE_LIST_HTML, "html.parser")
        mock_fetch_html.return_value = soup

        result = await scraper._scrape_single_subject("CS", limit=1)

        assert len(result) == 1
        assert result[0]["course_code"] == "CS 1110"

    @pytest.mark.unit
    @patch("scraper.scrapers.cornell.CornellScraper.fetch_html")
    async def test_scrape_single_subject_no_courses(
        self, mock_fetch_html, mock_cornell_db_session
    ):
        """Test scraping subject with no courses."""
        scraper = CornellScraper(mock_cornell_db_session)

        # Mock empty HTML response
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        mock_fetch_html.return_value = soup

        result = await scraper._scrape_single_subject("EMPTY")

        assert len(result) == 0

    @pytest.mark.unit
    @patch("scraper.scrapers.cornell.CornellScraper.fetch_html")
    async def test_scrape_all_subjects(self, mock_fetch_html, mock_cornell_db_session):
        """Test scraping all subjects from browse page."""
        scraper = CornellScraper(mock_cornell_db_session)

        # Mock responses - first call for browse page, subsequent for each subject
        soup_browse = BeautifulSoup(SAMPLE_CORNELL_SUBJECTS_HTML, "html.parser")
        soup_courses = BeautifulSoup(SAMPLE_CORNELL_COURSE_LIST_HTML, "html.parser")

        mock_fetch_html.side_effect = [soup_browse, soup_courses, soup_courses]

        result = await scraper._scrape_all_subjects()

        # Should have fetched browse page + 2 subject pages
        assert mock_fetch_html.call_count == 3
        # Should return courses from both subjects (2 courses per subject)
        assert len(result) == 4

    @pytest.mark.unit
    @patch("scraper.scrapers.cornell.CornellScraper.fetch_html")
    async def test_scrape_courses_specific_department(
        self, mock_fetch_html, mock_cornell_db_session
    ):
        """Test scraping courses for a specific department."""
        scraper = CornellScraper(mock_cornell_db_session)

        # Mock HTML response
        soup = BeautifulSoup(SAMPLE_CORNELL_COURSE_LIST_HTML, "html.parser")
        mock_fetch_html.return_value = soup

        result = await scraper.scrape_courses("CS")

        assert len(result) == 2
        assert all("course_code" in course for course in result)

    @pytest.mark.unit
    @patch("scraper.scrapers.cornell.CornellScraper._scrape_all_subjects")
    async def test_scrape_courses_all(self, mock_scrape_all, mock_cornell_db_session):
        """Test scraping all courses."""
        scraper = CornellScraper(mock_cornell_db_session)

        # Mock the _scrape_all_subjects method
        mock_courses = [
            {
                "course_code": "CS 1110",
                "title": "Intro to CS",
                "classes": [
                    {"class_number": "12345", "section": "001", "status": "open"}
                ],
            }
        ]
        mock_scrape_all.return_value = mock_courses

        result = await scraper.scrape_courses("ALL")

        mock_scrape_all.assert_called_once()
        assert result == mock_courses

    @pytest.mark.unit
    @patch("scraper.scrapers.cornell.CornellScraper.fetch_html")
    async def test_scrape_courses_with_limit(
        self, mock_fetch_html, mock_cornell_db_session
    ):
        """Test scraping with limit parameter."""
        scraper = CornellScraper(mock_cornell_db_session)

        # Mock HTML response
        soup = BeautifulSoup(SAMPLE_CORNELL_COURSE_LIST_HTML, "html.parser")
        mock_fetch_html.return_value = soup

        result = await scraper.scrape_courses("CS", limit=1)

        assert len(result) == 1
