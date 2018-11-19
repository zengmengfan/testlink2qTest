import requests
import json
from testlink import TestlinkAPIClient
from qTestClient import QtestClient
from utils import *



class Testlink2qTest:
    def __init__(self,testlinkclient,qtestclient):
        self.qclient=qtestclient
        self.tclient=testlinkclient

    def buildKeywordsMap(self,projectid,qtestprojectid):
        kwlist=self.getProjectKeywords(projectid)
        allow_values=list()
        for kw in kwlist:
            allow_values.append({"label":kw,"is_active":True})
        data={
            "label":"Keywords",
            "allowed_values":allow_values,
            "multiple":True,
            "data_type":17
        }
        res=self.qclient.createCaseField(qtestprojectid,data)
        kw_map=dict()
        for kw in res["allowed_values"]:
            kw_map[kw["label"]]=kw["value"]
        return kw_map

    def createFieldsAndBuildMaps(self,projectid,qtestprojectid,userlist,usermap,project_manager):
        self.keywords_map=self.buildKeywordsMap(projectid,qtestprojectid)
        self.user_map=self.qclient.buildUserMapAndAssignUsers(userlist,usermap,qtestprojectid)
        self.qclient.createCaseField(qtestprojectid,{"label":"Scope","data_type":1})
        priority_map=self.qclient.getFieldAllowedValues(qtestprojectid,"test-cases","Priority")
        maxp=0
        for p in priority_map:
            if maxp<priority_map[p]:
                maxp=priority_map[p]      
        self.maxp=maxp
        self.default_user=project_manager

    def extractCase(self,testprojectid,testcaseexternalid):
        case_content=self.tclient.getTestCase(testcaseexternalid=testcaseexternalid)[0]
        testcaseid=case_content["testcase_id"]
        version = case_content['version']
        case_all_version=list()
        kw=self.tclient.getTestCaseKeywords(testcaseid=testcaseid)
        keywords= list(kw[testcaseid].values())
        for v in range(int(version)):
            try: 
                case_v=tclient.getTestCase(testcaseexternalid=testcaseexternalid,version=v+1)[0]
            except Exception:
                continue
            fields={}
            fields['owner']=case_v['updater_login'] or case_v['author_login']
            fields['name']=case_v['name']
            fields['preconditions']=case_v['preconditions'].replace('\t','').replace('\n','')
            fields['summary']=case_v['summary'].replace('\t','').replace('\n','')
            fields['priority']=self.tclient.getTestCaseCustomFieldDesignValue(testprojectid=testprojectid,testcaseexternalid=testcaseexternalid,version=v+1,customfieldname='Case_Priority')
            fields['scope']=self.tclient.getTestCaseCustomFieldDesignValue(testprojectid=testprojectid,testcaseexternalid=testcaseexternalid,version=v+1,customfieldname='Scope')
            fields['steps']=""
            fields['expected_results']=""
            if type(case_v['steps'])== list:
                fields['steps']=case_v['steps'][0]["actions"].replace('\t','').replace('\n','')
                if "expected_results" in case_v['steps'][0]:
                    fields['expected_results']=case_v['steps'][0]["expected_results"].replace('\t','').replace('\n','')
            case_all_version.append(fields)
        return (case_all_version,keywords)

    def getProjectKeywords(self,projectid):
        kwdict=self.tclient.getProjectKeywords(projectid)
        kwlist=list()
        for k in kwdict:
            kwlist.append(kwdict[k])
        return kwlist

    def extactSuite(self,testsuiteid):
        suite=self.tclient.getTestSuiteByID(testsuiteid=testsuiteid)
        suite_content={}
        suite_content['name']=suite["name"]
        suite_content['details']=suite['details'].replace('\t','').replace('\n','')
        return suite_content    

    def update_single_case(self,testprojectid,qtestprojectid,testcaseexternalid,qcaseid,):
        case_all_version,keywords=self.extractCase(testprojectid,testcaseexternalid)
        for v in case_all_version:
            if not v["owner"] in self.user_map:
                owner=str([self.user_map[self.default_user]])
            else:
                owner=str([self.user_map[v["owner"]]])
            data={    
                "owner":owner,
                "name":v["name"],
                "priority": self.maxp+1-int(v["priority"] or 5),
                "scope": v["scope"],
                "summary": v["summary"],
                "preconditions": v["preconditions"],
                "step":v["steps"],
                'expected_results':v["expected_results"]
            }
            labels=str(list(map(lambda x: self.keywords_map[x],keywords)))
            update=self.qclient.buildUpdateCaseData(qtestprojectid,data,labels)
            self.qclient.updateCase(qtestprojectid,qcaseid,update)
            self.qclient.approveCase(qtestprojectid,qcaseid)

    def getTestCasesOfSuite(self,testsuiteid):
        raw_data=self.tclient.getTestCasesForTestSuite(testsuiteid=testsuiteid)
        first_level_case=list(filter(lambda x: x['parent_id']==testsuiteid, raw_data))
        first_level_id_order=sorted(list(map(lambda x:(x['id'],int(x['node_order'])),first_level_case)),key=lambda x:x[1])
        ordered_ids=[x[0] for x in first_level_id_order]
        return ordered_ids

    def getTestSuitesOfSuites(self,testsuiteid):
         raw_data=self.tclient.getTestSuitesForTestSuite(testsuiteid=testsuiteid)
         first_level_id_order=sorted(list(map(lambda x: (x,int(raw_data[x]['node_order'])),raw_data)),key=lambda x:x[1])
         ordered_ids=[x[0] for x in first_level_id_order]
         return ordered_ids

    def buildSuite(self,testlinkprojectid,testlinksuiteid,qtestprojectid,qtestparentid):
        suite_content=self.extactSuite(testlinksuiteid)
        qtestmoduleid=self.qclient.createModule(qtestprojectid,suite_content["name"],parentid=qtestparentid,detail=suite_content["details"])
        testcases=self.getTestCasesOfSuite(testsuiteid=testlinksuiteid)
        subsuites=self.getTestSuitesOfSuites(testsuiteid=testlinksuiteid)
        print('Migrating '+suite_content['name']+' ...')
        bar = ProgressBar(total = len(testcases))
        for case in testcases:
            case_content=self.tclient.getTestCase(testcaseid=case)[0]
            casename=case_content['name']
            testcaseexternalid=case_content['full_tc_external_id']
            qtestcaseid=qclient.createCase(qtestprojectid,qtestmoduleid,casename)
            self.update_single_case(testlinkprojectid,qtestprojectid,testcaseexternalid,qtestcaseid)
            bar.update()
        for suiteid in subsuites:
            self.buildSuite(testlinkprojectid,suiteid,qtestprojectid,qtestparentid=qtestmoduleid)


    def move_recursively(self,testprojectname,qtestprojectname,userlist,usermap,project_manager):
        testlinkprojectid=self.tclient.getProjectIDByName(testprojectname)
        qtestprojectid=self.qclient.createProject(qtestprojectname)
        self.createFieldsAndBuildMaps(testlinkprojectid,qtestprojectid,userlist,usermap,project_manager)
        top_module=self.qclient.createModule(qtestprojectid,testprojectname)
        modules=self.tclient.getFirstLevelTestSuitesForTestProject(testprojectid=testlinkprojectid)
        for suite in modules:
            self.buildSuite(testlinkprojectid,suite['id'],qtestprojectid,qtestparentid=top_module)


if __name__ == '__main__':
    with open("config.json") as f:
        c=f.read()
    config=json.loads(c)
    qclient=QtestClient(config["qtest_server_url"],config["qtesttoken"])
    tclient=TestlinkAPIClient(config["testlink_server_url"], config["testlink_devkey"])
    t2q=Testlink2qTest(tclient,qclient)
    qtestproject_list=config["qtestproject_list"]
    testlink_project_list=config["testlink_project_list"]
    userlist=config["project_members"]
    usermap=config["user_map"]
    project_manager=config["project_owner"]
    for testprojectname,qtestprojectname in zip(testlink_project_list,qtestproject_list):
        print("Migrating Project "+testprojectname+" ...")
        t2q.move_recursively(testprojectname,qtestprojectname,userlist,usermap,project_manager)
