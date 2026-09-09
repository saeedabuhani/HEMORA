def test_authentication(client,users):
    response=client.post('/api/auth/login',json={'email':'admin@test.local','password':'Pass123!'})
    assert response.status_code==200 and response.json()['role']=='ADMIN'
def test_authorization(client,users):
    token=client.post('/api/auth/login',json={'email':'patient@test.local','password':'Pass123!'}).json()['access_token']
    response=client.get('/api/audit',headers={'Authorization':f'Bearer {token}'})
    assert response.status_code==403
def test_invalid_login(client,users): assert client.post('/api/auth/login',json={'email':'admin@test.local','password':'wrong'}).status_code==401
