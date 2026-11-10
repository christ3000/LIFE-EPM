import json
from urllib.parse import parse_qs

import pytest

from app import worker


class ProviderResponse:
    status = 200

    def __init__(self, data: dict):
        self.data = json.dumps(data).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return self.data


def test_sms_worker_accepts_only_provider_successes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker.settings, "sms_provider", "africas_talking")
    monkeypatch.setattr(worker.settings, "sms_username", "sandbox")
    monkeypatch.setattr(worker.settings, "sms_api_key", "test-key")
    monkeypatch.setattr(worker.settings, "sms_sender", "EPM")
    monkeypatch.setattr(worker.settings, "sms_sandbox", True)
    captured = {}

    def open_request(request, timeout):
        captured["url"] = request.full_url
        captured["fields"] = parse_qs(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return ProviderResponse({
            "SMSMessageData": {
                "Recipients": [
                    {"status": "Success", "statusCode": "101"},
                    {"status": "Success", "statusCode": "101"},
                ]
            }
        })

    monkeypatch.setattr(worker, "urlopen", open_request)
    assert worker.send_bulk_sms(["+2250700000000", "+2250700000001"], "Réunion dimanche.") == {"submitted": 2}
    assert captured["url"] == "https://api.sandbox.africastalking.com/version1/messaging"
    assert captured["fields"] == {
        "username": ["sandbox"],
        "to": ["+2250700000000,+2250700000001"],
        "message": ["Réunion dimanche."],
        "from": ["EPM"],
    }
    assert captured["timeout"] == 20


@pytest.mark.parametrize(
    "recipients",
    [
        [{"status": "Success"}],
        [{"status": "Success"}, {"status": "Failed"}],
        [{"status": "Success"}, None],
    ],
)
def test_sms_worker_rejects_failed_or_incomplete_provider_results(
    monkeypatch: pytest.MonkeyPatch, recipients: list[dict | None]
) -> None:
    monkeypatch.setattr(worker.settings, "sms_provider", "africas_talking")
    monkeypatch.setattr(worker.settings, "sms_username", "sandbox")
    monkeypatch.setattr(worker.settings, "sms_api_key", "test-key")
    monkeypatch.setattr(worker.settings, "sms_sandbox", True)
    monkeypatch.setattr(
        worker,
        "urlopen",
        lambda *_args, **_kwargs: ProviderResponse({"SMSMessageData": {"Recipients": recipients}}),
    )

    with pytest.raises(RuntimeError):
        worker.send_bulk_sms(["+2250700000000", "+2250700000001"], "Réunion dimanche.")
