# Hackathon Friction Log

This file records the development and AWS onboarding issues encountered while building Speech-Resilient Alexa. The Bedrock, IAM policy discovery, and IAM policy-name validation issues were encountered directly during setup. The SMS entry records a constraint found while researching the planned SMS delivery path; SMS was not shipped, and Telegram was used for alerts instead.

## 1. Amazon Bedrock model access

- **Task attempted:** Use Amazon Nova Lite through the Bedrock Converse API as the project's LLM provider.
- **Steps taken:** Added the Bedrock provider to the application, attached `AmazonBedrockFullAccess` to the IAM user, attempted model calls in `us-east-1`, and requested a quota increase through AWS Support.
- **Expected result:** A successful Converse response from Nova Lite so the assistant could use Bedrock as its active brain.
- **Actual result:** The first call returned `AccessDeniedException: Your account is currently being verified`. Later calls returned `ValidationException: Operation not allowed` for Nova Lite and other tested models. The applied Nova 2 Lite quota was reported as 0, and two quota requests were denied. Anthropic models were unavailable for our country.
- **Severity:** Critical for the planned AWS-hosted brain; the rest of the project remained usable.
- **Workaround:** Switched the active LLM to Groq's free tier and kept Bedrock available as an alternative provider in the code.
- **Actionable suggestion:** Show account verification status and per-model access/quota in the Bedrock console, explain restrictions with a clear reason and expected resolution time, and provide a small default quota for hackathon accounts.

## 2. SMS delivery restrictions in Egypt

- **Task attempted:** Find a practical way to deliver emergency alerts to helpers by SMS.
- **Steps taken:** Checked the AWS SNS SMS and AWS End User Messaging documentation for Egypt and the requirements for sending messages from a new account.
- **Expected result:** Send a test alert to a verified phone number using the SMS sandbox.
- **Actual result:** The documented Egypt setup requires a registered sender ID, a letter of authorization, and company documents. New accounts also have a low monthly SMS spending limit, making this route impractical for an individual hackathon project.
- **Severity:** High for the planned SMS alert feature.
- **Workaround:** Used the Telegram Bot API for helper alerts, behind a single notification interface so SMS can be added later.
- **Actionable suggestion:** Allow sandbox messages to verified recipients in every supported country and provide a country-by-country registration checklist at the start of the SMS documentation.

## 3. Finding the Amazon Location IAM permission

- **Task attempted:** Grant the application permission to call Amazon Location Service `ReverseGeocode`.
- **Steps taken:** Searched IAM managed policies for terms such as “geospatial” and tried policies whose names appeared relevant, including SageMaker geospatial policies.
- **Expected result:** Find a clearly named Amazon Location policy or an obvious `ReverseGeocode` permission.
- **Actual result:** The policies found were for SageMaker geospatial rather than Amazon Location. The required action used the `geo-places` prefix, which was not apparent from the IAM search results.
- **Severity:** Medium; it delayed setup of address lookup for emergency alerts.
- **Workaround:** Created an inline IAM policy allowing `geo-places:ReverseGeocode`.
- **Actionable suggestion:** Make Amazon Location policies easier to find by searching “location” or “geospatial” in IAM, and link a least-privilege policy example from each Location API page.

## 4. IAM policy-name validation feedback

- **Task attempted:** Create an inline IAM policy for the Amazon Location permission.
- **Steps taken:** Entered a policy name containing unsupported characters and submitted the form.
- **Expected result:** The console would identify the unsupported character in the policy name.
- **Actual result:** The console displayed both “The specified value for policyName is invalid…” and “Policy name is required,” without identifying the invalid character.
- **Severity:** Low; the policy could still be created after correcting the name.
- **Workaround:** Re-entered the policy name using a simpler valid name.
- **Actionable suggestion:** Highlight unsupported characters and show one precise validation message instead of reporting that the name is missing.

