from bcc.models import User


def test_api_status(client):
    status = client.status()
    assert isinstance(status, dict)
    print(status)


def test_api_user_add(client, username, displayname, password):
    user = client.add_user(username, displayname, password)
    assert isinstance(user, User)
