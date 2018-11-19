import requests
from requests import get as GET, post as POST, put as PUT
import time
import datetime
from utils import *

requests.packages.urllib3.disable_warnings() 

class QtestClient:
    def __init__(self,base_url,access_token=None,username=None,password=None):
        self.base_url=base_url
        if access_token:
            self.token=access_token
            self.token_type="bearer"
        elif not username and not password:
            self._get_token(username,password)
        else:
            raise Exception("No authorization is provided")

    def _get_token(self,username,password):
        head={"Content-Type": "application/x-www-form-urlencoded"
               #"Authorization" : "Basic bWVuZy1mYW4uemVuZ0Bhc21sLmNvbTo="
        }
        payload={
            "username":username,
            "password":password,
            "grant_type":"password",
        }
        r=requests.post(self.base_url+'/oauth/token',auth=(username,""),data=payload,headers=head,verify=False)
        self.token=r.json()["access_token"]
        self.token_type=r.json()["token_type"]

    @retry(tries=5,interval=5)
    def req(self,method,api,data=None):
        head={ "Content-Type": "application/json",
               "Authorization" : self.token_type+" "+self.token
        }
        r=method(self.base_url+api,headers=head,verify=False,json=data)
        return r.json() 

    def createProject(self,projectname):
        now=datetime.datetime.utcnow()
        end=now+datetime.timedelta(days=3000)
        start_date=now.strftime('%Y-%m-%dT%H:%M:%S') + now.strftime('.%f')[:4] + 'Z'
        end_date=end.strftime('%Y-%m-%dT%H:%M:%S') + end.strftime('.%f')[:4] + 'Z'
        data={
            "name":projectname,
            "start_date":start_date,
            "end_date":end_date
        }
        return self.req(POST,'/api/v3/projects',data)['id']

    def createModule(self,projectid,name,parentid=None,detail=None):
        data={
          "name": name,
          "description": "Default",
        }
        if parentid:
            data['parent_id']=parentid
        if detail:
            data['description']=detail
        return self.req(POST,'/api/v3/projects/%s/modules' % projectid, data)['id']

    def createCase(self,projectid,parentid,name):
        data={
        "name": name,
        "parent_id":parentid,
        }
        return self.req(POST,'/api/v3/projects/%s/test-cases' % projectid, data)["id"]

    def createCaseField(self,projectid,data):
        return self.req(POST,'/api/v3/projects/%s/settings/test-cases/fields' % projectid,data)

    def getFieldAllowedValues(self,projectid,objecttype,fieldname):
        fields=self.req(GET,'/api/v3/projects/%s/settings/%s/fields' % (projectid,objecttype))
        values=dict()
        for field in fields:
            if field["label"]==fieldname:
                for v in field["allowed_values"]:
                    values[v["label"]]=v["value"]
        return values

    def getFieldIdsByLabels(self,projectid,objecttype,labels):
        fields=self.req(GET,'/api/v3/projects/%s/settings/%s/fields' % (projectid,objecttype))
        label_id=dict()
        for field in fields:
            if field["label"] in labels:
                label_id[field["label"]]=field["id"]
        return label_id

    def updateCase(self,projectid,caseid,data):
        return self.req(PUT,'/api/v3/projects/%s/test-cases/%s' % (projectid,caseid), data)

    def approveCase(self,projectid,caseid):
        return self.req(PUT,'/api/v3/projects/%s/test-cases/%s/approve'% (projectid,caseid))
    
    def buildUserMapAndAssignUsers(self,userlist,usermap,projectid):
        user_map=dict()
        user_ids=list()
        for user in userlist:
            res=self.req(GET,'/api/v3/users/search?username=%s' % user)
            if user in usermap:
                user=usermap[user]
            user_map[user]=res["items"][0]["id"]
            user_ids.append(res["items"][0]["id"])
        invite_data={
            "project_id": projectid,
            "user_ids": user_ids,
            "profile": {"id":5}
        }
        self.req(POST,'/api/v3/users/projects',invite_data)
        return user_map

    def buildUpdateCaseData(self,qtestprojectid,case_content,keywords):
        properties=["Assigned To","Priority","Keywords","Scope"]
        label2id=self.getFieldIdsByLabels(qtestprojectid,'test-cases',properties)
        data={
            "name": case_content["name"],
            "properties": [
                {
                    "field_id":label2id["Assigned To"] ,
                    "field_value": case_content["owner"],
                },
                {
                    "field_id": label2id["Priority"],
                    "field_value": case_content["priority"]
                },
                {
                     "field_id": label2id["Keywords"],
                     "field_value": keywords
                 },
                {
                    "field_id": label2id["Scope"],
                    "field_value": case_content["scope"]
                }
            ],
            "description": case_content["summary"],
            "precondition": case_content["preconditions"],
            "test_steps": [
                {
                  "description": case_content["step"],
                  "expected": case_content["expected_results"]
                }
             ]
        }
        return data



if __name__ == '__main__':
    import json 
    with open("config.json") as f:
        c=f.read()
    config=json.loads(c)
    qc=QtestClient(config["qtest_server_url"],config["qtesttoken"])
    print(qc.createProject('test_project'))
