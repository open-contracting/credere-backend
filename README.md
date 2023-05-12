Dockerfile added to the project

-in order to deploy first build an image using

docker build -t {image_name} .

-then you can run it using the following command

docker run -d --name {container_name} -p 8000:8000 {image_name}

-Changes may require you to re create the image, in that case delete it using:

docker rmi <your-image-id>

-for testing purposes you can run the app inside a virtual env using:

uvicorn app.main:app --reload

-Black formater extention for VS code is being used for formatting, no config needed (ext id ms-python.black-formatter)

-settings configured according to https://fastapi.tiangolo.com/advanced/settings/ guidelines

-versioning will be handled


Cognito SDK https://docs.aws.amazon.com/code-library/latest/ug/python_3_cognito-identity-provider_code_examples.html

Scheduled processes https://pypi.org/project/fastapi-scheduler/

Files S3 https://aws.amazon.com/sdk-for-python/

AWS SES (emails) https://docs.aws.amazon.com/code-library/latest/ug/
python_3_ses_code_examples.html
