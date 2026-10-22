from datetime import datetime
from hashlib import sha256
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class ReminderEmailError(RuntimeError):
    """The reminder email address could not be registered with Amazon SNS."""


class ReminderEmail:
    """Creates an isolated SNS topic for an account and asks SNS to verify its email address."""

    def __init__(
        self,
        region: str,
        topic_prefix: str = "speech-alexa-reminder",
        scheduler_role_arn: str = "",
        timezone: str = "Africa/Cairo",
        schedule_group: str = "default",
    ) -> None:
        self._sns = boto3.client("sns", region_name=region)
        self._scheduler = boto3.client("scheduler", region_name=region)
        self._topic_prefix = topic_prefix
        self._scheduler_role_arn = scheduler_role_arn
        self._timezone = timezone
        self._schedule_group = schedule_group

    def subscribe(self, company_id: str, user_id: str, email: str) -> str:
        # A separate topic per address prevents one account's reminders reaching another account's subscribers.
        key = sha256(f"{company_id}\0{user_id}\0{email}".encode()).hexdigest()[:32]
        try:
            topic = self._sns.create_topic(Name=f"{self._topic_prefix}-{key}")
            topic_arn = topic["TopicArn"]
            self._sns.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email)
            return topic_arn
        except (BotoCoreError, ClientError, KeyError) as error:
            raise ReminderEmailError("Could not send the email verification request through Amazon SNS.") from error

    def confirmed(self, topic_arn: str, email: str) -> bool:
        try:
            token = None
            while True:
                args = {"TopicArn": topic_arn}
                if token:
                    args["NextToken"] = token
                page = self._sns.list_subscriptions_by_topic(**args)
                if any(
                    item["Endpoint"].casefold() == email.casefold() and item["SubscriptionArn"] != "PendingConfirmation"
                    for item in page["Subscriptions"]
                ):
                    return True
                token = page.get("NextToken")
                if not token:
                    return False
        except (BotoCoreError, ClientError, KeyError) as error:
            raise ReminderEmailError("Could not check the Amazon SNS email confirmation.") from error

    def schedule(
        self, company_id: str, user_id: str, request_id: str, topic_arn: str, email: str, details: dict
    ) -> str:
        if not self._scheduler_role_arn:
            raise ReminderEmailError("Reminder scheduling is not configured in AWS yet.")
        if not self.confirmed(topic_arn, email):
            raise ReminderEmailError("Confirm the reminder email before setting a reminder.")
        try:
            timezone = ZoneInfo(self._timezone)
            scheduled_at = datetime.fromisoformat(str(details["scheduled_at"]))
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone)
            scheduled_at = scheduled_at.astimezone(timezone)
            if scheduled_at <= datetime.now(timezone):
                raise ReminderEmailError("That reminder time has passed. Please choose a future time.")
        except ZoneInfoNotFoundError as error:
            raise ReminderEmailError("The configured reminder timezone is not available.") from error
        except (KeyError, TypeError, ValueError) as error:
            raise ReminderEmailError("I couldn't determine the reminder date and time. Please say them again.") from error

        request_key = sha256(f"{company_id}\0{user_id}\0{request_id}".encode()).hexdigest()[:32]
        schedule_name = f"reminder-{request_key}"
        what, when = str(details.get("what", "something")), str(details.get("when", ""))
        message = f"Reminder: {what}\nScheduled for {when} ({self._timezone})."
        try:
            self._scheduler.create_schedule(
                Name=schedule_name,
                GroupName=self._schedule_group,
                ScheduleExpression=f"at({scheduled_at.strftime('%Y-%m-%dT%H:%M:%S')})",
                ScheduleExpressionTimezone=self._timezone,
                FlexibleTimeWindow={"Mode": "OFF"},
                ActionAfterCompletion="DELETE",
                Target={
                    "Arn": topic_arn,
                    "RoleArn": self._scheduler_role_arn,
                    "Input": message,
                },
            )
            return f"Reminder scheduled: {what}, {when}."
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "ConflictException":
                return f"Reminder scheduled: {what}, {when}."
            raise ReminderEmailError("AWS couldn't schedule that reminder. Please try again.") from error
        except BotoCoreError as error:
            raise ReminderEmailError("AWS couldn't schedule that reminder. Please try again.") from error
