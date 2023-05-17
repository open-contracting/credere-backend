import json

data = {
    "OCP_USER": "Adrian",
    "LINK-TO-WEB-VERSION": "www.google.com",
    "OCP_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/logoocp.jpg",
    "SET_PASSWORD_IMAGE_LINK": "https://adrian-personal.s3.sa-east-1.amazonaws.com/set_password.png",
    "LOGIN_URL": "www.google.com",
    "TWITTER_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/twiterlogo.png",
    "FB_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/facebook.png",
    "LINK_LOGO": "https://adrian-personal.s3.sa-east-1.amazonaws.com/link.png",
    "TWITTER_LINK": "www.google.com",
    "FACEBOOK_LINK": "www.google.com",
    "LINK_LINK": "www.google.com",

}

# Convert it into a JSON string
json_string = json.dumps(data)
# print (json_string);
# To escape the quotes in the string, you can use another call to json.dumps()
escaped_json_string = json.dumps(json_string)

print(escaped_json_string)
