#!/usr/bin/env python3
"""MVP API contracts with isolated SQLite, signed webhooks and a fake Stripe transport."""
import copy
import hashlib
import hmac
import json
import sys
import tempfile
import threading
import time
from contextlib import closing
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from backup import create_backup,restore_backup

def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);server.DATA=root/'data';server.UPLOADS=root/'uploads';server.DB=server.DATA/'test.db';server.ADMIN_PASSWORD='test-only-password';server.COMMERCE_ENABLED=False
        server.init_db()
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{httpd.server_address[1]}'
        cookie='';csrf='';calls=[]
        def req(path,data=None,headers=None):
            raw=json.dumps(data).encode() if data is not None else None
            hdr={'Content-Type':'application/json','Cookie':cookie,'X-CSRF-Token':csrf}|(headers or {})
            request=Request(base+'/api'+path,data=raw,headers=hdr)
            try:
                with urlopen(request,timeout=10) as r: return r.status,json.loads(r.read()),dict(r.headers)
            except HTTPError as e: return e.code,json.loads(e.read()),dict(e.headers)
        def ok(path,data=None,expected=200):
            code,result,headers=req(path,data);assert code==expected,(path,code,result);return result
        def fake_stripe(method,endpoint,params=None,idempotency_key=None):
            calls.append((method,endpoint,params,idempotency_key))
            return {'id':'cs_'+idempotency_key.split(':')[-1],'url':'https://checkout.stripe.com/c/pay/'+idempotency_key.split(':')[-1]}
        try:
            code,result,headers=req('/admin/login',{'password':'test-only-password'});assert code==200
            cookie=headers['Set-Cookie'].split(';')[0];csrf=result['csrfToken']
            assert 'HttpOnly' in headers['Set-Cookie'] and 'SameSite=Strict' in headers['Set-Cookie']
            assert req('/admin/stock',{},headers={'X-CSRF-Token':''})[0]==403
            content=ok('/admin/content');original=copy.deepcopy(content['content'])
            for section,value in original.items():
                result=ok('/admin/content',{'section':section,'value':value,'version':content['version']});content=result
                assert result['content'][section]==value,section
            changed=copy.deepcopy(original['pages']);changed['shop']['titleLineOne']='Updated heading'
            content=ok('/admin/content',{'section':'pages','value':changed,'version':content['version']})
            assert content['content']['home']==original['home']
            assert req('/admin/content',{'section':'pages','value':changed,'version':0})[0]==409
            event={'id':'event-test','title':'A night','date':'01.10.26','isoDate':'2026-10-01','location':'Rome','ticketUrl':'https://example.com/tickets','visible':True}
            content=ok('/admin/content',{'section':'live','value':[event],'version':content['version']})
            assert ok('/content')['live']==[event]
            content=ok('/admin/content',{'section':'live','value':ok('/content')['live'],'version':content['version']})
            assert content['content']['live']==[event]
            product={'name':'API Product','sku':'API-1','priceCents':1250,'meta':'','description':'','image':'','alt':'','active':True,'variants':[]}
            pid=ok('/admin/products',product)['id']
            ok('/admin/stock',{'productId':pid,'delta':10,'reason':'test receipt'})
            catalog=ok('/admin/products')['products'];p=next(p for p in catalog if p['id']==pid)
            ok('/admin/products',product|{'id':pid,'version':p['version'],'description':'New text','stock':999})
            p=next(p for p in ok('/admin/products')['products'] if p['id']==pid);assert p['stock']==10
            content=ok('/admin/content',{'section':'home','value':original['home'],'version':content['version']})
            assert next(p for p in ok('/admin/products')['products'] if p['id']==pid)['stock']==10
            payload={'requestKey':'a'*24,'email':'buyer@example.com','customer':{'name':'Buyer','address':'Test street','city':'Roma','postcode':'00100','country':'IT','phone':''},'shippingMethod':'shipping','items':[{'productId':pid,'quantity':1,'priceCents':1}]}
            assert req('/checkout',payload)[0]==503
            assert req('/checkout/quote',payload)[0]==503
            assert req('/stripe/webhook',{'id':'ignored'})[0]==503
            assert not ok('/admin/orders')['orders']
            assert ok('/config')['commerceEnabled'] is False
            server.COMMERCE_ENABLED=True
            server.STRIPE_SECRET_KEY='test-placeholder';server.STRIPE_WEBHOOK_SECRET='signed-test';server.PUBLIC_BASE_URL='https://example.com';server.stripe_request=fake_stripe
            assert req('/checkout',payload)[0]==409 # no shipping price invented
            conf=ok('/admin/settings');settings=conf['settings'];settings['shipping']['zones']=[{'name':'Italy','countries':['IT'],'priceCents':600},{'name':'Europe','countries':['DE','FR'],'priceCents':1200}]
            conf=ok('/admin/settings',{'value':settings,'version':conf['version']})
            assert ok('/checkout/quote',payload)['totalCents']==1850
            international=copy.deepcopy(payload);international['customer']['country']='DE'
            assert ok('/checkout/quote',international)['shippingCents']==1200
            pickup=payload|{'shippingMethod':'pickup'};assert req('/checkout/quote',pickup)[0]==409
            settings['shipping'].update(pickupAddress='Test location',pickupInstructions='Arrange a time',freeThresholdCents=1000)
            conf=ok('/admin/settings',{'value':settings,'version':conf['version']})
            assert ok('/checkout/quote',payload)['shippingCents']==0
            assert ok('/checkout/quote',pickup)['shippingCents']==0
            for quantity in [0,-1,1.5,True,'2',100]:
                bad=payload|{'items':[{'productId':pid,'quantity':quantity}]};assert req('/checkout/quote',bad)[0]==400
            for key in ['name','address','city','postcode','country']:
                bad=copy.deepcopy(payload);bad['customer'][key]='';assert req('/checkout/quote',bad)[0]==400,key
            first=ok('/checkout',payload,201);again=ok('/checkout',payload,201);assert first==again and len(calls)==1
            assert calls[0][2]['payment_method_types[0]']=='card'
            with closing(server.db()) as c:
                row=c.execute('SELECT * FROM orders WHERE id=?',(first['orderId'],)).fetchone()
                assert int(server.datetime.fromisoformat(row['reservation_expires_at']).timestamp())==calls[0][2]['expires_at']
                assert row['total_cents']==1250
            assert req('/orders/status?id='+first['orderId'])[0]==400
            assert req('/orders/status?id='+first['orderId'],headers={'X-Order-Token':'wrong'})[0]==404
            assert req('/orders/status?id='+first['orderId'],headers={'X-Order-Token':first['statusToken']})[1]['paymentStatus']=='PENDING'
            event={'id':'evt-1','type':'checkout.session.completed','data':{'object':{'id':'cs_'+first['orderId'],'metadata':{'order_id':first['orderId']},'payment_intent':'pi_test','payment_status':'paid','amount_total':1250,'currency':'eur'}}}
            def webhook(e):
                raw=json.dumps(e).encode();stamp=str(int(time.time()));signature=hmac.new(server.STRIPE_WEBHOOK_SECRET.encode(),stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
                return req('/stripe/webhook',e,{'Stripe-Signature':f't={stamp},v1={signature}'})
            assert webhook(event)[0]==200;assert webhook(event)[0]==200
            ok('/admin/orders/status',{'orderId':first['orderId'],'fulfillmentStatus':'SHIPPED','tracking':'TRACK-1','notes':'packed'})
            event['id']='evt-same-session';assert webhook(event)[0]==200
            order=ok('/admin/orders')['orders'][0];assert order['shipping_status']=='SHIPPED' and order['payment_status']=='PAID' and order['address']=='Test street'
            with closing(server.db()) as c:
                assert c.execute('SELECT stock,reserved_stock FROM products WHERE id=?',(pid,)).fetchone()[:]==(9,0)
                assert c.execute('SELECT COUNT(*) FROM mail_outbox').fetchone()[0]==2
            refund={'id':'refund-1','type':'charge.refunded','data':{'object':{'payment_intent':'pi_test','refunded':True,'amount_refunded':1250}}}
            assert webhook(refund)[0]==200 and ok('/admin/orders')['orders'][0]['payment_status']=='REFUNDED'
            # Variant inventory is independent, with stable identifiers and stock zero unavailable.
            vp=product|{'name':'Variant product','sku':'VAR-P','variants':[{'sku':'VAR-M','size':'M','color':'black','active':True},{'sku':'VAR-L','size':'L','color':'black','active':True}]}
            vidp=ok('/admin/products',vp)['id'];vp=next(p for p in ok('/admin/products')['products'] if p['id']==vidp)
            v1,v2=vp['variants'];ok('/admin/stock',{'productId':vidp,'variantId':v1['id'],'delta':2,'reason':'variant receipt'})
            assert req('/checkout/quote',payload|{'items':[{'productId':vidp,'variantId':v2['id'],'quantity':1}]})[0]==409
            duplicate=payload|{'items':[{'productId':vidp,'variantId':v1['id'],'quantity':2}]*2}
            assert req('/checkout/quote',duplicate)[0]==409
            # Signed expiration releases once; late payment cannot silently sell unavailable stock.
            server.RATE_BUCKETS.clear()
            late=ok('/checkout',payload|{'requestKey':'b'*24},201)
            expire={'id':'expired-1','type':'checkout.session.expired','data':{'object':{'id':'cs_'+late['orderId'],'metadata':{'order_id':late['orderId']}}}}
            assert webhook(expire)[0]==200;assert webhook(expire)[0]==200
            ok('/admin/stock',{'productId':pid,'delta':-9,'reason':'remove remaining stock'})
            paid=copy.deepcopy(event);paid['id']='late-payment';paid['data']['object']['id']='cs_'+late['orderId'];paid['data']['object']['metadata']['order_id']=late['orderId']
            assert webhook(paid)[0]==200
            late_order=next(o for o in ok('/admin/orders')['orders'] if o['id']==late['orderId'])
            assert late_order['payment_status']=='PAID' and late_order['issue']=='PAID_WITHOUT_STOCK' and late_order['stock_applied']==0
            # Backup remains internally consistent and carries uploaded assets.
            (server.UPLOADS/'test.png').write_bytes(b'asset fixture')
            archive=create_backup(server.DB,server.UPLOADS,server.DATA/'backups')
            restore_backup(archive,root/'restored')
            assert (root/'restored/uploads/test.png').read_bytes()==b'asset fixture'
            import sqlite3
            with closing(sqlite3.connect(root/'restored/data/kosmik.db')) as c: assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==2
            ok('/admin/logout',{});assert req('/admin/orders')[0]==401
            print('CHECKOUT / CMS / ADMIN / SHIPPING / VARIANTS / WEBHOOK / BACKUP API PASS')
        finally: httpd.shutdown();httpd.server_close()

if __name__=='__main__': main()

