"""HTTPS SMS/email gateway. No console-code or pretend-success fallback."""
import os
import httpx
from app.services.auth import AuthError

def configuration():
    url=os.environ.get('AUTH_DELIVERY_URL','');token=os.environ.get('AUTH_DELIVERY_TOKEN','')
    if not url.startswith('https://') or not token:
        raise AuthError('IDENTITY_DELIVERY_UNAVAILABLE','SMS/email gateway is not configured',503)
    return url,token

def send(*,challenge_id,channel,destination,code,ttl_seconds):
    url,token=configuration()
    with httpx.Client(timeout=10,follow_redirects=False) as client:
        response=client.post(url.rstrip('/')+'/otp',headers={'Authorization':'Bearer '+token,'Idempotency-Key':challenge_id},
            json={'request_id':challenge_id,'channel':channel,'destination':destination,'code':code,'ttl_seconds':ttl_seconds})
        response.raise_for_status();body=response.json()
    if body.get('request_id')!=challenge_id or body.get('status')!='ACCEPTED':raise RuntimeError('OTP delivery was not accepted')
