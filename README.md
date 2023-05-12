#Credere Backend

## Basic setup runnig the app

First create a docker image with the following command:
```
docker build -t {image_name} .
```

After that you can run it using the following command or docker interface
```
docker run -d --name {container_name} -p 8000:8000 {image_name}
```

Changes may require you to re create the image, in that case delete it using:
```
docker rmi <your-image-id>
```

 ## Basic setup for development

for testing purposes you can run the app inside a virtual env using:
```
uvicorn app.main:app --reload
```

.env file needs to be created with the proper environment variables

## identation and formatting

Black formater extention for VS code is being used for formatting, no config needed (ext id ms-python.black-formatter)

settings configured according to https://fastapi.tiangolo.com/advanced/settings/ guidelines

versioning will be handled using an environment variable in .env file and following https://semver.org/


