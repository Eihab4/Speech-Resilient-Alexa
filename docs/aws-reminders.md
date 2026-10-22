# AWS email reminders

The app creates one standard SNS topic per signed-in account and verified email address. EventBridge Scheduler publishes the reminder directly to that topic at the requested time. No Lambda is needed for this flow.

## AWS console setup

Use the same region as the app's `AWS_REGION` (the example defaults to `us-east-1`).

1. Open **IAM → Roles → Create role**. Choose **AWS service** and **EventBridge Scheduler** as the trusted service.
2. Create an inline permissions policy for that role that allows `sns:Publish` on only the reminder topics, for example `arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:speech-alexa-reminder-*`.
3. Copy the role ARN into `.env` as `REMINDER_SCHEDULER_ROLE_ARN`. Set `REMINDER_TIMEZONE` to the user's IANA timezone, such as `Africa/Cairo`.
4. Configure the credentials used by the local MCP server with permissions for `sns:CreateTopic`, `sns:Subscribe`, and `sns:ListSubscriptionsByTopic` on the reminder topics; `scheduler:CreateSchedule` on the `default` schedule group; and `iam:PassRole` for only the role from step 1, restricted to `scheduler.amazonaws.com`.
5. Start the server. In **People who help me**, save the reminder email and click the confirmation link sent by AWS SNS. Reopen the section; it should show **Email address confirmed**.
6. Say a reminder with a specific future date and time and confirm it. The app reports success only after EventBridge Scheduler accepts the schedule.

The server's AWS credentials can come from an AWS CLI profile; do not put access keys in the repository or frontend. The end user does not need an AWS account. A separate SNS topic per email prevents another account's reminders from being delivered to them.

## Configuration

```dotenv
AWS_REGION=us-east-1
REMINDER_EMAIL_TOPIC_PREFIX=speech-alexa-reminder
REMINDER_SCHEDULER_ROLE_ARN=arn:aws:iam::YOUR_ACCOUNT_ID:role/YOUR_SCHEDULER_ROLE
REMINDER_TIMEZONE=Africa/Cairo
REMINDER_SCHEDULE_GROUP=default
```
