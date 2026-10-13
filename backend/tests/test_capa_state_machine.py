import pytest

from app.domain.capa import require_evidence_for_close, transition


@pytest.mark.parametrize(
    "status,action,expected",
    [
        ("待执行", "start", "执行中"),
        ("执行中", "submit_verify", "待验收"),
        ("待验收", "close", "已关闭"),
        ("待验收", "reject", "执行中"),
    ],
)
def test_legal_transitions(status, action, expected):
    new_status, err = transition(status, action)
    assert err is None
    assert new_status == expected


@pytest.mark.parametrize(
    "status,action",
    [
        ("待执行", "close"),
        ("待执行", "submit_verify"),
        ("待执行", "reject"),
        ("执行中", "start"),
        ("执行中", "close"),
        ("执行中", "reject"),
        ("待验收", "start"),
        ("待验收", "submit_verify"),
        ("已关闭", "start"),
        ("已关闭", "close"),
        ("待执行", "unknown"),
    ],
)
def test_illegal_transitions(status, action):
    new_status, err = transition(status, action)
    assert err is not None
    assert new_status == status


def test_close_requires_non_empty_evidence():
    assert require_evidence_for_close("close", None) is not None
    assert require_evidence_for_close("close", "") is not None
    assert require_evidence_for_close("close", "   ") is not None
    assert require_evidence_for_close("close", "照片已上传，压力表回绿") is None
    # non-close actions do not require evidence
    assert require_evidence_for_close("start", None) is None
    assert require_evidence_for_close("reject", None) is None
