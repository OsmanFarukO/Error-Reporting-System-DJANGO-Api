Error Reporting System DJANGO Api
=============
For report human been issues you can use this api.

<h3>Prerequest<h3>

`$ cd error-reporting-system-django-api`

`$ ./prerequirements.sh`

`$ pip install -r requirements.txt`

You must set mysql db options at `settings.py` . After then in project directory;

`$ python manage.py makemigrations` for create migrations and;

`$ python manage.py migrate` for migrate model to database.

<h3>For run project<h3>

`$ python manage.py runserver`