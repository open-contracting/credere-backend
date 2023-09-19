# Email templates

This project uses SES services from AWS to store email templates and send emails.

## AWS SES Configuration

### Verified identities

If our AWS SES account is in sandbox status (most likely if it's an AWS account for testing purposes), to be able to send or receive mail through SES, we need to add both the sender's and receiver's email as verified identities.

### Receiving failure and error notifications from SES

In the AWS Simple Notification Service, we must add:

- A Topic and a Subscription. The subscription must include the email to which the notifications will be sent.
  An access policy must also be added to the subscription, allowing the SES service to use it.

In AWS SES, for the verified entity sending the mail, we must set:

- Notifications: In the Notifications tab, we must select the notifications we want to receive (Bounce, Delivery Feedback, Complaint Feedback) and link it to the topic we created through the AWS Simple Notification Service.

- A configuration set, that is linked to our AWS Simple email Service Topic, and in the "Event types" tabs que must select the eventes que want to track (Hard bounces, Complaints, Rejects, Rendering failures)

## Managing email templates

There are two types of templates, the ones stored in the source code and AWS and the ones used by the source code only.

### AWS templates

The ones stored in AWS starts with the "aws_" file name prefix.

Currently, there are only two, aws_main.html and aws_main_es.html. 
These templates contain the base html code for all the emails, including the email header, styles and footer.
These templates also contains the {CONTENT} parameter, which will be replaced by `email_utility.py` with the actual
email's content, depending on the type of email to be sent.

#### Creating the template for the first time

First we must install the AWS CLI.

For AWS CLI installation instructions please refer to the docs at:
[https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

Then, we need to use the [create-template](https://docs.aws.amazon.com/cli/latest/reference/ses/create-template.html) command, for example:

```bash
aws ses create-template --cli-input-json file://xxxx.json --profile credere-admin
```

Where the JSON file must look like:

```json
{
  "Template": {
    "TemplateName": "credere-main-en",
    "SubjectPart": "{SUBJECT}",
    "HtmlPart": "(aws_main.html as a minified HTML)"
  }
}
```

Where:
- TemplateName: must be credere-main-en for the English template and credere-main-es for the Spanish one.
- SubjectPart: must be {SUBJECT} as the subject is set by `email_utility.py` depeding on the email type
- HtmlPart: must be the minified version of aws_main.html or aws_main_es.html

#### Updating an existing template

First, edit the aws_main.html or aws_main_es.html files.
Then, generate the minified version of the updated file.
Finally, generate the same JSON file used for creating the template, but with the
updated minified HTML file as HtmlPart.
Then run:

```bash
aws ses update-template --cli-input-json file://xxxx.json --profile credere-admin
```

### Email CONTENT templates

All the other templates are only subsections of the email with the specific message
to be sent as part of that email.
To update an existing CONTENT template you should edit it directly and then deploy the changes to the server.
To create and use a new template you should create the HTML file, and then include the new template file name
and subjects in English and Spanish in `email_utility.TEMPLATE_FILES`.

## Parameters in templates

Templates are in HTML. To introduce a parameter you can add **{{PARAMETER_NAME}}** as text inside any HTML attribute or text, for replace text or URLs for example.

In the code, when using the **send_templated_email** method from the SES client, add the **PARAMETER_NAME** as key in the dict passed as **TemplateData** parameter of the method.

If the parameter is an URL for an image, you can follow the URL structure use in the function **generate_common_data** where the ENV variable **app_settings.images_base_url** is used to create the full URL.

## Sending emails for testing

You can use the [send-templated-email](https://docs.aws.amazon.com/cli/latest/reference/ses/send-templated-email.html) command, example:

```bash
aws ses send-templated-email -cli-input-json file:///home//xxxx.json --profile credere-admin
```

### JSON to Send Mail Example

```json
{
  "Source": "Credere_mail_test <credere@noreply.open-contracting.org>",
  "Template": "credere-main-es",
  "Destination": {
    "ToAddresses": ["credereadmin@open-contracting.org"]
  },
  "TemplateData": "{\"AWARD_SUPPLIER_NAME\": \"VENDOR XX\", \"TENDER_TITLE\": \"FOOD PROVIDER\""}"
}
```
