import requests,logging,json,os,psutil
from decouple import config
from pathlib import Path
from datetime import datetime


BASE_DIR =  Path(__file__).resolve().parent
INFO_FILE  = Path(BASE_DIR,"data.json")

logging.basicConfig(
    filename= f"{BASE_DIR}/logs.log",
    filemode='a',
    format='[%(asctime)s] [%(levelname)s] [%(funcName)s] : %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.WARNING)


LOAD = 20.0 # max server load 

ACTIVE_TIME  = 1800 # time that function should be running defualt is 30 minutes

ZONE_ID  =  config("zone_id") #zone id

RULES =  config("rules_id").split(",") #rules that y want to control

API = "https://api.cloudflare.com/client/v4/zones/%s/firewall/rules" % ZONE_ID #api url

HEADERS  = {
            'X-Auth-Email': config("email"),
            'X-Auth-Key': config("auth_key"),
            'Content-Type': 'application/json'
            }

def fetch(action :  str = "GET" , rule_id : str =  None, data : dict = {} ) -> dict:
    url =  API
    response =  requests.get(url,headers=HEADERS)
    if action == "PUT":
        url = API+f"/{rule_id}"
        data =  json.dumps(data)
        response =  requests.put(url,headers=HEADERS,data=data)
    return response.json() if response.status_code == 200  else logging.warning("could not fetch %s err %s" % (url,response.status_code) )

def compare(modified_date : datetime) ->  int:
    return  int((datetime.now()-modified_date).seconds/60) >= ACTIVE_TIME 

def set_time():
    data = json.dumps({"date":str(datetime.now())})
    with  open(INFO_FILE,"w") as f:
        f.write(data)

def running_for():
    if os.path.exists(INFO_FILE):
        with open(INFO_FILE,"r") as f:
            data  =  json.loads(f.read())
            date = datetime.strptime(data["date"],"%Y-%m-%d %H:%M:%S.%f")
            return compare(date)
    return False
            
def list_rules():
    response  =  fetch()
    result =  response.get("result")
    if not result:
        logging.error("could not get rules list ")
    return [ rule for rule in result if rule.get("id") in RULES]

def get_rules_ids():
    response  =  fetch()
    result =  response.get("result")
    if not result:
        logging.error("could not get rules list ")
    for rule in result:
        print("%s  => %s" % ( rule.get("id") ,rule.get("description")))

    
def over_load() -> bool:
    logging.debug("loading is %s" % psutil.cpu_percent())
    return psutil.cpu_percent() >= LOAD

def turn_on(rule : dict ):
    setting_time = set_time()

    rule["paused"] = False

    rule_id  = rule.get("id")

    return fetch(action="PUT",rule_id=rule_id,data=rule)  

def turn_off(rule : dict) :
    rule["paused"] = True

    rule_id  = rule.get("id")

    return fetch(action="PUT",rule_id=rule_id,data=rule)  


def main():
    _load   = over_load()
    rules   = list_rules()
    too_long  =  running_for()

    for rule in rules:
        logging.debug("proccessnig %s" % rule.get("id"))
        if _load:
            turn_on_ = turn_on(rule)
        else:
            if too_long:
                turn_off_ = turn_off(rule)

if __name__ == "__main__":
    #get_rules_ids()
    main()