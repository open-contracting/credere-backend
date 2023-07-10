# Email templates

This project uses SES services from AWS to store email templates and send emails.

## AWS SES console configuration

### Verified identities

If our AWS SES account is in sandbox status (most likely if it's an AWS account for testing purposes), to be able to send or receive mail through SES, we need to add both the sender's and receiver's email as verified identities.

### Receiving failure and error notifications from SES

In the AWS Simple Notification Service, we must add:

- A Topic and a Subscription. The subscription must include the email to which the notifications will be sent.
  An access policy must also be added to the subscription, allowing the SES service to use it.

In AWS SES, for the verified entity sending the mail, we must set:

- Notifications: In the Notifications tab, we must select the notifications we want to receive (Bounce, Delivery Feedback, Complaint Feedback) and link it to the topic we created through the AWS Simple Notification Service.

- A configuration set, that is linked to our AWS Simple email Service Topic, and in the "Event types" tabs que must select the eventes que want to track (Hard bounces, Complaints, Rejects, Rendering failures)

## AWS CLI use to create, update and send mails

first we must install the AWS CLI.

For AWS CLI installation instrucctions please refer to the docs at:
[https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

Once we have AWS CLI installed, we can use the command specific for SES.

For a full list of SES commands, please refer to:

[https://docs.aws.amazon.com/cli/latest/reference/ses/index.html](https://docs.aws.amazon.com/cli/latest/reference/ses/index.html)

Examples of the commands most frequently used:

## Create template

### AWS SES Command Example

```bash
aws ses create-template --cli-input-json file:///home//xxxx.json --profile credere-admin
```

### JSON to Create Template Example

```json
{
  "Template": {
    "TemplateName": "credere-AccessToCreditSchemeForMSMEs",
    "SubjectPart": "Credere - Intro",
    "HtmlPart": "<html lang='en'><head> <meta charset='utf-8' /> <meta name='viewport' content='width=device-width, initial-scale=1.0' /> <title>New Credit Application</title> </body></html>"
  }
}
```

## Update template

### AWS SES Command Example

```bash
aws ses update-template --cli-input-json file:///home//xxxx.json --profile credere-admin
```

(the Json would be the same as the one used in create template)

## Send mail

### AWS SES Command Example

```bash
aws ses send-templated-email -cli-input-json file:///home//xxxx.json --profile credere-admin
```

### JSON to Send Mail Example

```json
{
  "Source": "Credere_mail_test <credere@noreply.open-contracting.org>",
  "Template": "credere-AccessToCreditSchemeForMSMEs",
  "Destination": {
    "ToAddresses": ["credereadmin@open-contracting.org"]
  },
  "TemplateData": "{\"AWARD_SUPPLIER_NAME\": \"VENDOR XX\", \"TENDER_TITLE\": \"FOOD PROVIDER\""}"
}
```
