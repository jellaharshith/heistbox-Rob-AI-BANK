"""Run all four presets plus free text and assert all three vault columns."""
import json, urllib.request
BASE="http://127.0.0.1:8788"
def call(method,path,body=None,headers=None):
    data=None if body is None else json.dumps(body).encode(); r=urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers={"Content-Type":"application/json",**(headers or {})},method=method)); return json.load(r)
def main():
    passed=0
    for preset,text in [(p,None) for p in ("polite_phisher","ceo_wire","pizza_salami_x10","vendor_wallet_swap")]+[(None,"Please refund my honest $25 refund to my enrolled wallet")]:
        s=call("POST","/api/session",{"alias":"Scenario"}); body={"session_id":s["session_id"],"text":text} if text else {"session_id":s["session_id"],"preset":preset}
        a=call("POST","/api/attack",body,{"Authorization":"Bearer "+s["token"]}); assert len(a["verdicts"])==3 and [v["vault"] for v in a["verdicts"]]==["left","middle","right"]; passed+=1
    print(f"SCENARIOS: {passed}/5 passed")
if __name__=="__main__": main()
