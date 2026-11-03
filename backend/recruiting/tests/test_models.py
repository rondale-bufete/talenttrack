import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from recruiting.models import Application
from .factories import make_application, make_candidate, make_job

pytestmark = pytest.mark.django_db
S = Application.Status


def test_new_application_starts_as_applied():
    assert make_application().status == S.APPLIED


@pytest.mark.parametrize("start, expected", [
    (S.APPLIED, S.SCREENING),
    (S.SCREENING, S.INTERVIEW),
    (S.INTERVIEW, S.OFFER),
    (S.OFFER, S.HIRED),
])
def test_advance_follows_the_pipeline(start, expected):
    app = make_application(status=start)
    app.advance()
    assert app.status == expected


@pytest.mark.parametrize("final", [S.HIRED, S.REJECTED])
def test_final_statuses_cannot_advance(final):
    app = make_application(status=final)
    with pytest.raises(ValidationError):
        app.advance()


def test_cannot_skip_steps():
    app = make_application()
    with pytest.raises(ValidationError):
        app.transition_to(S.OFFER)


def test_can_reject_from_any_open_step():
    for start in (S.APPLIED, S.SCREENING, S.INTERVIEW, S.OFFER):
        app = make_application(status=start)
        app.transition_to(S.REJECTED)
        assert app.status == S.REJECTED


def test_candidate_cannot_apply_twice_to_same_job():
    cand, job = make_candidate(), make_job()
    make_application(cand, job)
    with pytest.raises(IntegrityError):
        make_application(cand, job)
