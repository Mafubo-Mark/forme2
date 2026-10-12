import os, tempfile, pathlib, sys
os.environ['FORME_DATABASE_URL']='sqlite:///' + tempfile.mktemp(suffix='.db')
os.environ['FORME_DATA_DIR']=tempfile.mkdtemp()
os.environ['FORME_SECURE_COOKIE']='0'
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import app
from fastapi.testclient import TestClient

def test_complete_flow_and_isolation():
    a=TestClient(app.app); b=TestClient(app.app); admin=TestClient(app.app)
    assert a.get('/api/customer/session').status_code==401
    assert admin.get('/api/admin/users').status_code==401
    for client,email,username in [(a,'one@example.test','one'),(b,'two@example.test','two')]:
        r=client.post('/api/customer/register',json=dict(email=email,username=username,password='Password123!'))
        assert r.status_code==200,r.text
        assert 'httponly' in r.headers['set-cookie'].lower()
        assert 'password' not in str(r.json()['user'])
    assert b.post('/api/customer/register',json=dict(email='one@example.test',username='three',password='password123')).status_code==409
    assert a.post('/api/customer/login',json=dict(identifier='one@example.test',password='wrong')).status_code==401
    a.post('/api/customer/logout')
    assert a.post('/api/customer/login',json=dict(identifier='one@example.test',password='Password123!')).status_code==200
    assert a.patch('/api/customer/profile',json=dict(full_name='Test User',phone='12345678')).status_code==200
    video=b'\x00\x00\x00\x18ftypmp42'+b'0'*100
    r=a.post('/api/uploads/init',json=dict(filename='test.mp4',content_type='video/mp4',byte_size=len(video))).json()
    upload=r['uploadId']
    assert b.put(r['uploadUrl'],content=video).status_code==404
    assert a.put(r['uploadUrl'],content=b'bad').status_code==400
    assert a.put(r['uploadUrl'],content=video).status_code==200
    assert a.post(f'/api/uploads/{upload}/complete').status_code==200
    r=a.post('/api/customer/submissions',json=dict(upload_id=upload,template_id='01',color='Ocean Blue',material='Durable Nylon',inspiration='<script>alert(1)</script>'))
    assert r.status_code==200,r.text
    sid=r.json()['submissionId']
    assert b.get('/api/customer/submissions').json()['items']==[]
    assert b.get(f'/api/customer/submissions/{sid}').status_code==404
    assert b.get(f'/api/customer/submissions/{sid}/files/video').status_code==404
    assert a.get(f'/api/customer/submissions/{sid}/files/video').content==video
    assert a.post('/api/customer/orders',json=dict(submission_id=sid)).status_code==409
    assert admin.post('/api/admin/login',json=dict(username='forme',password='123456')).status_code==200
    assert a.get('/api/admin/users').status_code==401
    assert admin.get('/api/admin/users').status_code==200
    assert admin.patch(f'/api/admin/submissions/{sid}',json=dict(status='ready',model_stage='ready',quote_hkd='399.50',admin_note='Reviewed')).status_code==200
    assert a.get(f'/api/customer/submissions/{sid}').json()['quote_hkd']=='399.50'
    assert admin.put(f'/api/admin/submissions/{sid}/model',content=b'glTF' + b'0'*20,headers={'x-file-name':'final.glb'}).status_code==200
    assert a.get(f'/api/customer/submissions/{sid}/files/model').status_code==200
    payload=dict(submission_id=sid,amount_hkd='0.01',recipient_name='Customer',recipient_phone='12345678',address_line='Test Street',region='Hong Kong',district='Central')
    r=a.post('/api/customer/orders',json=payload); assert r.status_code==200,r.text
    order=r.json(); oid=order['id']; assert order['amount_hkd']=='399.50'
    assert a.post('/api/customer/orders',json=payload).json()['id']==oid
    assert b.get('/api/customer/orders').json()['items']==[]
    assert a.post(f'/api/customer/orders/{oid}/confirm-receipt').status_code==409
    assert admin.patch(f'/api/admin/orders/{oid}',json=dict(order_status='printing')).status_code==409
    payment=a.post(f'/api/customer/orders/{oid}/payments',json=dict(method='FPS',reference='TEST123')).json()['paymentId']
    assert a.put(f'/api/customer/payments/{payment}/proof',content=b'\x89PNG\r\n\x1a\n' + b'0'*30).status_code==200
    assert b.get(f'/api/customer/payments/{payment}/proof').status_code==404
    assert admin.patch(f'/api/admin/payments/{payment}',json=dict(status='confirmed',review_note='Verified')).status_code==200
    assert a.get('/api/customer/orders').json()['items'][0]['payment_status']=='paid'
    assert admin.patch(f'/api/admin/payments/{payment}',json=dict(status='confirmed')).status_code==409
    for status in ['printing','shipped']:
        r=admin.patch(f'/api/admin/orders/{oid}',json=dict(order_status=status,carrier='SF',tracking_number='TEST001')); assert r.status_code==200,r.text
    assert a.post(f'/api/customer/orders/{oid}/confirm-receipt').status_code==200
    final=a.get('/api/customer/orders').json()['items'][0]; assert final['delivery']['confirmed_at']; assert final['order_status']=='delivered'
    user_id=a.get('/api/customer/session').json()['user']['id']
    report=admin.get(f'/api/admin/users/{user_id}').json(); assert report['submissions'][0]['events']; assert report['orders'][0]['delivery']['confirmed_at']
    assert a.post('/api/customer/logout',headers={'origin':'https://evil.example'}).status_code==403
    a.post('/api/customer/logout'); assert a.get('/api/customer/session').status_code==401
    with app.Factory() as s:
        user=s.get(app.User,user_id); assert user.password_hash.startswith('scrypt$'); assert 'Password123!' not in user.password_hash
    app.engine.dispose()
    import sqlite3
    restored=sqlite3.connect(':memory:'); source=sqlite3.connect(os.environ['FORME_DATABASE_URL'].split('///')[1]); source.backup(restored)
    assert restored.execute('select count(*) from users').fetchone()[0]==2
    assert restored.execute('select order_status from orders').fetchone()[0]=='delivered'
