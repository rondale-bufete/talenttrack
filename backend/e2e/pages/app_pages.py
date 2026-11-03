from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from .base import BasePage, tid


class DashboardPage(BasePage):
    path = "/"

    def stat(self, name):
        return int(self.text_of(tid(f"stat-{name}")))


class JobsPage(BasePage):
    path = "/jobs"

    def create_job(self, title, department="", skills="", min_years=0):
        self.type(tid("job-title"), title)
        self.type(tid("job-department"), department)
        self.type(tid("job-skills"), skills)
        self.type(tid("job-min-years"), min_years)
        self.click(tid("job-submit"))

    def job_titles(self):
        return [el.text for el in self.find_all(tid("job-row-title"))]

    def wait_for_job(self, title):
        self.wait.until(lambda d: title in self.job_titles())

    def row_for(self, title):
        self.wait_for_job(title)
        for row in self.find_all(tid("job-row")):
            if row.find_element(*tid("job-row-title")).text == title:
                return row
        raise AssertionError(f"job {title!r} not listed")

    def run_screening(self, title):
        self.row_for(title).find_element(*tid("screen-button")).click()
        return self.wait.until(
            lambda d: self.row_for(title).find_element(*tid("screen-result"))
        ).text

    def form_error(self):
        return self.text_of(tid("job-form-error"))


class CandidatesPage(BasePage):
    path = "/candidates"

    def add(self, name, email, skills="", years=0):
        self.type(tid("cand-name"), name)
        self.type(tid("cand-email"), email)
        self.type(tid("cand-skills"), skills)
        self.type(tid("cand-years"), years)
        self.click(tid("cand-submit"))

    def names(self):
        return [r.find_element(By.TAG_NAME, "td").text for r in self.find_all(tid("candidate-row"))]

    def wait_for_candidate(self, name):
        self.wait.until(lambda d: name in self.names())

    def filter(self, text):
        self.type(tid("cand-filter"), text)

    def form_error(self):
        return self.text_of(tid("cand-form-error"))


class PipelinePage(BasePage):
    path = "/pipeline"

    def open_for_job(self, job_id):
        self.driver.get(f"{self.base_url}{self.path}?job={job_id}")
        self.find(tid("pipeline-job"))
        return self

    def add_applicant(self, name):
        select_el = self.find(tid("apply-candidate"))
        self.wait.until(lambda d: name in [o.text for o in Select(select_el).options])
        Select(select_el).select_by_visible_text(name)
        self.click(tid("apply-submit"))
        self.wait_for_card(name, "applied")

    def names_in(self, stage):
        column = self.find(tid(f"column-{stage}"))
        return [c.find_element(By.CLASS_NAME, "app-name").text
                for c in column.find_elements(*tid("app-card"))]

    def wait_for_card(self, name, stage):
        self.wait.until(lambda d: name in self.names_in(stage))

    def _card(self, name, stage):
        column = self.find(tid(f"column-{stage}"))
        for card in column.find_elements(*tid("app-card")):
            if card.find_element(By.CLASS_NAME, "app-name").text == name:
                return card
        raise AssertionError(f"{name!r} not in {stage}")

    def advance(self, name, from_stage, to_stage):
        self._card(name, from_stage).find_element(*tid("advance")).click()
        self.wait_for_card(name, to_stage)

    def reject(self, name, from_stage):
        self._card(name, from_stage).find_element(*tid("reject")).click()
        self.wait_for_card(name, "rejected")

    def score_of(self, name, stage):
        return self._card(name, stage).find_element(*tid("app-score")).text

    def score_all(self):
        self.click(tid("pipeline-screen"))

    def wait_for_score(self, name, stage, expected):
        self.wait.until(lambda d: self.score_of(name, stage) == str(expected))
