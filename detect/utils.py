from channels.db import database_sync_to_async
from oauth2_provider.models import AccessToken
from django.contrib.auth.models import User
from detect.models import Employee

@database_sync_to_async
def get_user_from_oauth(oauth_token):
    usrid = AccessToken.objects.get(token=oauth_token).user_id
    print('userid ', usrid)
    emp = Employee.objects.get(user_id=usrid)
    return {'corp_id': emp.corp_id, 'user_id': usrid}