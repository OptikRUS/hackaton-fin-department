import json
from pathlib import Path
from typing import Any

import pytest

from src.core.analytics.exceptions import InvalidAnalyticsError
from src.infra.api.analytics.schemas import AnalyticsUploadRequest


def comparison_upload() -> dict[str, Any]:
    body = json.loads(
        (Path(__file__).parents[1] / "data/android-analytics-upload.json").read_text()
    )
    body["facts"] = [
        {
            "eventId": "answer-1",
            "gameRunId": body["gameRunId"],
            "episodeId": "episode-1",
            "actionId": "submission-1",
            "sequence": 1,
            "contextFamily": "compare_amounts",
            "detail": {
                "_type": "question_answer",
                "questionId": "question-1",
                "attempt": 1,
                "task": {"_type": "compare_amounts", "left": 20, "right": 10, "chosen": "LEFT"},
            },
        }
    ]
    return body


@pytest.mark.parametrize("pick_larger", [False, True, "absent"])
def test_comparison_target_accepts_boolean_or_legacy_absence(pick_larger: bool | str) -> None:
    body = comparison_upload()
    if pick_larger != "absent":
        body["facts"][0]["detail"]["task"]["pickLarger"] = pick_larger
    params = AnalyticsUploadRequest.parse(body).to_domain()
    params.validate(idempotency_key=body["batchId"])
    task = params.facts[0]["detail"]["task"]
    if pick_larger == "absent":
        assert "pickLarger" not in task
    else:
        assert task["pickLarger"] is pick_larger


@pytest.mark.parametrize("invalid", [None, "false", "true", 0, 1, [], {}])
def test_comparison_target_rejects_non_boolean_values(invalid: object) -> None:
    body = comparison_upload()
    body["facts"][0]["detail"]["task"]["pickLarger"] = invalid
    with pytest.raises(InvalidAnalyticsError):
        AnalyticsUploadRequest.parse(body).to_domain().validate(idempotency_key=body["batchId"])


def test_comparison_target_preserves_legacy_digest_and_distinguishes_smaller_target() -> None:
    body = comparison_upload()
    legacy = AnalyticsUploadRequest.parse(body).to_domain()
    assert (
        legacy.request_digest()
        == "992044548b31e602cc9c1a8381098e39e36371371ef3a028510640200518d4d8"
    )
    body["facts"][0]["detail"]["task"]["pickLarger"] = False
    smaller = AnalyticsUploadRequest.parse(body).to_domain()
    smaller.validate(idempotency_key=body["batchId"])
    assert smaller.request_digest() != legacy.request_digest()
    assert smaller.original_digests() != legacy.original_digests()
