import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from celery import Celery

from app.config import get_settings

settings = get_settings()
# Configuration Celery pour les traitements asynchrones et les envois SMS.
celery_app = Celery(
    "life_epm",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
logger = logging.getLogger("life_epm.worker")


@celery_app.task(name="life_epm.send_sms")
def send_sms(phone_number: str, message: str) -> None:
    send_bulk_sms([phone_number], message)


@celery_app.task(name="life_epm.send_bulk_sms", autoretry_for=(URLError, TimeoutError), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_bulk_sms(phone_numbers: list[str], message: str) -> dict[str, int]:
    if settings.sms_provider != "africas_talking":
        raise RuntimeError("SMS provider is disabled or unsupported; refusing to send.")
    if not settings.sms_username or not settings.sms_api_key:
        raise RuntimeError("Africa's Talking credentials are not configured.")
    if not phone_numbers or len(phone_numbers) > 500:
        raise ValueError("SMS batch must contain between 1 and 500 phone numbers.")

    endpoint = (
        "https://api.sandbox.africastalking.com/version1/messaging"
        if settings.sms_sandbox
        else "https://api.africastalking.com/version1/messaging"
    )
    fields = {
        "username": settings.sms_username,
        "to": ",".join(phone_numbers),
        "message": message,
    }
    if settings.sms_sender:
        fields["from"] = settings.sms_sender
    request = Request(
        endpoint,
        data=urlencode(fields).encode("utf-8"),
        headers={"apiKey": settings.sms_api_key, "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"Africa's Talking rejected the SMS batch (HTTP {response.status}).")
            provider_response = json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(f"Africa's Talking rejected the SMS batch (HTTP {error.code}).") from None
    except URLError:
        logger.exception("Could not reach the Africa's Talking SMS endpoint.")
        raise
    if not isinstance(provider_response, dict):
        raise RuntimeError("Africa's Talking returned an invalid SMS batch response.")
    response_data = provider_response.get("SMSMessageData")
    recipients = response_data.get("Recipients") if isinstance(response_data, dict) else None
    if (
        not isinstance(recipients, list)
        or len(recipients) != len(phone_numbers)
        or any(not isinstance(recipient, dict) for recipient in recipients)
    ):
        raise RuntimeError("Africa's Talking returned an incomplete SMS batch response.")
    failed = sum(recipient.get("status") != "Success" for recipient in recipients)
    if failed:
        raise RuntimeError(f"Africa's Talking did not accept {failed} SMS recipient(s).")
    logger.info("Africa's Talking accepted an SMS batch for %s recipients.", len(recipients))
    return {"submitted": len(recipients)}
