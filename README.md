# Complete Blog

Template:
* https://startbootstrap.com/theme/clean-blog

Functions
* Contact form sends email with the given message (in order to work, you have to create data.py file with variables FROM_EMAIL, PASSWORD, TO_EMAIL)
* All passwords are salted and hashed through pbkdf2:sha256 method
* Flask_login is handling login status, so in specific situations, users can see different things than others
* All data are stored with SQLAlchemy in SQLite DB

Privileges:
* First user in DB with id=1 is always admin
* Admin can create/delete/edit all posts and create/delete all comments
* Users can add comments and delete their own posts
* Non-logged users can only browse all posts

DB Schema:   
![db_schema](https://user-images.githubusercontent.com/66170274/117628937-f1c04180-b179-11eb-854b-a3ac49da1416.png)

Libraries:
* flask
* flask_bootstrap
* flask_ckeditor
* datetime
* werkzeug.security
* flask_sqlalchemy
* flask_login
* smtplib

