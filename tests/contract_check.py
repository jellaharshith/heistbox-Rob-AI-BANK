"""Live smoke check for the v1.1 REST/WebSocket contract (server must be on 8788)."""
import json, sys, urllib.request
BASE="http://127.0.0.1:8788"
def req(method,path,body=None,headers=None):
    data=None if body is None else json.dumps(body).encode(); h={"Content-Type":"application/json",**(headers or {})}
    r=urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=h,method=method)); return json.load(r)
def main():
    checks=0; health=req("GET","/api/health"); assert health["version"]=="1.1.0" and all(k in health for k in ("db","llm","offline_mode","ws_clients","uptime_s")); checks+=1
    s=req("POST","/api/session",{"alias":"Contract Check"}); assert all(k in s for k in ("session_id","token","entitlement","presets","ws_path")); checks+=1
    a=req("POST","/api/attack",{"session_id":s["session_id"],"preset":"polite_phisher"},{"Authorization":"Bearer "+s["token"]}); assert len(a["verdicts"])==3 and {v["vault"] for v in a["verdicts"]}=={"left","middle","right"}; checks+=1
    lb=req("GET","/api/leaderboard"); assert "entries" in lb and "generated_at" in lb; checks+=1
    p=req("GET","/api/poster/"+s["session_id"]); assert "stats" in p and "generated_at" in p; checks+=1
    print(f"CONTRACT CHECK: {checks}/5 checks passed")
if __name__=="__main__": main()
