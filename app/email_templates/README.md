# Email templates

To be able to create, update, or test email sending, we must install the AWS CLI.

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
    "ToAddresses": ["test@gmail.com"]
  },
  "TemplateData": "{\"AWARD_SUPPLIER_NAME\": \"VENDOR XX\", \"TENDER_TITLE\": \"FOOD PROVIDER\""}"
}
```
