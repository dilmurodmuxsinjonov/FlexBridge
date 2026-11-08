"""Bound authentication bodies and prevent caching of bearer/verification secrets."""
import json

class IAMHTTPMiddleware:
    def __init__(self,app,max_bytes=131072):self.app,self.max_bytes=app,max_bytes

    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or not scope.get('path','').startswith((
            '/api/v1/auth/', '/api/v1/me/security', '/api/v1/me/contacts',
            '/api/v1/me/candidate', '/api/v1/me/availability', '/api/v1/candidates/',
            '/api/v1/matching/', '/api/v1/opportunities/feed', '/api/v1/files/',
            '/api/v1/organizations', '/api/v1/operator/verification-cases', '/api/v1/invitations/',
            '/api/v1/operations/')):
            return await self.app(scope,receive,send)
        def redact_invitation():
            if scope.get('path','').startswith('/api/v1/invitations/'):
                parts=scope['path'].split('/')
                if len(parts)>4:parts[4]='[REDACTED]'
                scope['path']='/'.join(parts)
                scope['raw_path']=scope['path'].encode('utf-8')
                scope['query_string']=b''
        data=bytearray()
        while True:
            message=await receive()
            if message['type']=='http.disconnect':
                redact_invitation()
                return
            data.extend(message.get('body',b''))
            if len(data)>self.max_bytes:
                redact_invitation()
                body=json.dumps({'detail':{'code':'AUTH_BODY_TOO_LARGE'}}).encode()
                await send({'type':'http.response.start','status':413,'headers':[(b'content-type',b'application/json'),(b'cache-control',b'no-store')]})
                return await send({'type':'http.response.body','body':body})
            if not message.get('more_body',False):break
        delivered=False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered=True
                return {'type':'http.request','body':bytes(data),'more_body':False}
            return await receive()
        async def private_send(message):
            if message['type']=='http.response.start':
                # Uvicorn formats its access-log URL when response.start is sent.
                redact_invitation()
                headers=[(k,v) for k,v in message.get('headers',[]) if k.lower() not in (b'cache-control',b'pragma',b'referrer-policy')]
                message={**message,'headers':headers+[(b'cache-control',b'no-store'),(b'pragma',b'no-cache'),(b'referrer-policy',b'no-referrer')]}
            await send(message)
        try:
            await self.app(scope,replay,private_send)
        except BaseException:
            redact_invitation()
            raise
