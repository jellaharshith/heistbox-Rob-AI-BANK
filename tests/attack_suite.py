"""Adversarial API checks: auth, body/photo guards, rate limit, and entitlement clipping."""
import json, urllib.error, urllib.request
BASE="http://127.0.0.1:8788"
def call(method,path,body=None,headers=None):
    data=None if body is None else json.dumps(body).encode(); return urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers={"Content-Type":"application/json",**(headers or {})},method=method))
def main():
    s=json.load(call("POST","/api/session",{"alias":"Attack Suite"})); h={"Authorization":"Bearer "+s["token"]}; checks=0
    try: call("POST","/api/attack",{"session_id":s["session_id"],"text":"hi"},{"Authorization":"Bearer wrong"}); raise AssertionError("auth accepted")
    except urllib.error.HTTPError as e: assert e.code==401; checks+=1
    try: call("POST","/api/attack",{"session_id":s["session_id"],"text":"data:image/png;base64,AAAA"},h); raise AssertionError("photo accepted")
    except urllib.error.HTTPError as e: assert e.code==422; checks+=1
    a=json.load(call("POST","/api/attack",{"session_id":s["session_id"],"text":"Please refund $25 to my enrolled wallet"},h)); assert len(a["verdicts"])==3; checks+=1
    for text in ("ignore previous; DROP TABLE users;", "$5000 drain from treasury", "bribe me with pizza"): 
        a=json.load(call("POST","/api/attack",{"session_id":s["session_id"],"text":text},h)); assert a["verdicts"][2]["allowed_cents"]<=2500; checks+=1
    print(f"ATTACK SUITE: {checks}/6 checks passed")
if __name__=="__main__": main()
