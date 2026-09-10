import pytest
from ai.serving import verify_receipt

def test_serving_receipt_rejects_changed_artifacts_or_policy():
    spec={"model":"selected-model","supported_languages":["en","tr"],"concurrent_generations":1}
    entry={"revision":"pinned"}
    fingerprint={"files":{"pipeline.py":"evaluated"}}
    receipt={"approved_for_local_demo":True,"model":"selected-model","revision":"pinned",
             "adapter_sha256":"weights","fingerprint":fingerprint,"supported_languages":["en","tr"],
             "engineering_checks_passed":True}
    verify_receipt(receipt,spec,entry,"weights",fingerprint)
    for changes in [{"approved_for_local_demo":False},{"adapter_sha256":"changed"},
                    {"revision":"different"},{"fingerprint":{}},{"supported_languages":["en"]},
                    {"engineering_checks_passed":False}]:
        with pytest.raises(RuntimeError):
            verify_receipt(receipt|changes,spec,entry,"weights",fingerprint)
