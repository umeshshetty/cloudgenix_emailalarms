#!/usr/bin/env python

"""
Python2.7 Module for Interaction with the Cloudgenix API.

**Version:** v1.0


#### Synopsis
Intended to be used for Colgate or any other Client using Cloudgenix SDWAN to use the Cloudgenix API for report events via e-mail.
Usage of this module requires knwoledge of Python2.7 and using standard libraries like e-mail and scheduler.

"""

__author__ = "Umesh Shetty"
__email__ = "umesh_shetty@colpal.com"
__status__ = "Development"
__verison__ = '0.1'


# Import CloudGenix SDK
import cloudgenix

# Import CloudGenix json, smtplib, datetime, cloudgenix_idname
import json
import smtplib
import datetime
import cloudgenix_idname
import gspread
from oauth2client.service_account import ServiceAccountCredentials


scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('Google Project.json',scope)    

# Create CloudGenix API constructor
cp_sess = cloudgenix.API()

# Class contructor for cloudgenix_idname
cp_idnames = cloudgenix_idname



class Ids(object):
    """
    Class to use the cloudgenix_idname library.
    This class returns a simple dictionary containing id's to description mapping.
    For reporting the id's retrned by the response object can be matched against this
    dictionary to display names rather than ID's to the end user.
    """
  
    def ids(self):

        self.cp_idnames = cloudgenix_idname  # class contructor for cloudgenix_idname
        try:
            self.cp_ids = self.cp_idnames.generate_id_name_map(cp_sess) # stores dictionary mapping in cp_ids variable.
        except TypeError:
            print "ID's methods timedout"
            pass
            

#end_time = datetime.datetime.isoformat(datetime.datetime.utcnow())
#start_time = datetime.datetime.isoformat(datetime.datetime.utcnow()- datetime.timedelta(hours=2))

def start_altime():
    client = gspread.authorize(creds)
    sheet = client.open('SDWAN ALARMS').sheet1
    rowsize = sheet.row_count
    if rowsize < 2:
        start_alarm_time = datetime.datetime.isoformat(datetime.datetime.utcnow())
    
    elif rowsize > 2:
        start_alarm_time = sheet.cell(rowsize,4).value +'Z'
    return start_alarm_time



class Alarms(object):
    """
    Class method to query the Cloudgenix API for the Alarms in the system
    """

    def __init__(self):
#        self.lastalarm_time = datetime.datetime.isoformat(datetime.datetime.utcnow())
        self.lastalarm_time = start_altime()

        """
        At class initialization sets the time to current time in UTC. This counter will
        change during execution of other methods in the class and help if returning
        new Alarms.
        """

    def alarmdata(self):
        """
        Class method to collect alarmdata
        """
        
        self._query_data = {"limit":{"count":30,"sort_on":"time","sort_order":"descending"},"view":{"summary":False},"end_time":"",
                           "start_time":"","severity":[],"query":{"site":[],"category":[],
                            "code":['NETWORK_DIRECTINTERNET_DOWN','PEERING_EDGE_DOWN','PEERING_CORE_DOWN', 'NETWORK_VPNLINK_DOWN',
                                    'DEVICEHW_POWER_LOST','DEVICEHW_INTERFACE_DOWN','NETWORK_PRIVATEWAN_UNREACHABLE','NETWORK_DIRECTPRIVATE_DOWN','DEVICEHW_DISKUTIL_PARTITIONSPACE',
                                    'DEVICEHW_MEMUTIL_SWAPSPACE','DEVICEHW_DISKENC_SYSTEM','DEVICEIF_ADDRESS_DUPLICATE','DEVICESW_GENERAL_PROCESSRESTART','DEVICESW_GENERAL_PROCESSSTOP',
                                    'DEVICESW_MONITOR_DISABLED','DEVICESW_GENERAL_PROCESSRESTART','DEVICESW_IMAGE_UNSUPPORTED','DEVICEHW_INTERFACE_HALFDUPLEX','DEVICESW_FPS_LIMIT_EXCEEDED',
                                    'DEVICESW_CONCURRENT_FLOWLIMIT_EXCEEDED','DEVICESW_LICENSE_VERIFICATION_FAILED','DEVICESW_TOKEN_VERIFICATION_FAILED','APPLICATION_FLOWCTRL_APPUNREACHABLE',
                                    'OPERATOR_SIGNUP_TOKEN_DISABLED']
                                    ,"correlation_id":[],"type":["alarm"]}}

        self._alarms = json.loads(json.dumps(cp_sess.post.events_query(self._query_data).cgx_content, indent = 4)) #Returns all alarms and stores in the variable

        try:
            self.alarms_list = self._alarms["items"] #Extracts all alarms from the Alarmdata and stores it in a List of alarms

        except KeyError:
            print " Connection Error to the CG API "

        return self.alarms_list
      
  

    def new_alarms(self):
        """
        Class method to identify new alarm from the alarm list using the lastalarmtime as the delta.
        """
   
        self.n_alarms = [] #sets the new alarms list as empty list at initiation

        print  self.lastalarm_time
        for i in range(len(self.alarms_list)): #iteration over the list if all alarms
            if self.alarms_list[i]["time"] > self.lastalarm_time:
                """
                Checks if the alarm being iterated has a timestamp greater than lastalarm_time.
                At program start the lastarm_time is set to the current time in the system.
                This ensures any alarms if seen after program start is considered as new alarm.
                """
                               
                self.n_alarms.append(self.alarms_list[i])
                """
                If the alarm matches the above condition it will be added to the new alarms list.
                This new alarms list can then be used for reporting alarm using e-mail.
                """
                    
            i+=1
        self.n_alarms.reverse()
        return self.n_alarms


    def curralarm(self):
        self.alarmholder = []
        self.alerted = []
        

class Sites(object):
    """
    Class for extracting the Colgate Sites data using the get method.
    """
     
    def sitesdata(self):
        """
        Class method sitesdata to query and :store sitesdata in variables.
        """
        self._cp_sitesraw = json.loads(json.dumps(cp_sess.get.sites().cgx_content, indent = 4 ))
        """
        Variable to store the raw sites data
        """
        try:
            self.cp_sites_list = self._cp_sitesraw["items"]
            
        except TypeError:
            print "Error fetching Data"
            pass
        """
        Variable to store the actual sites in a list format from the raw sites data.
        """

        return self.cp_sites_list
    

    def sitestatus(self):
        self.cp_sites_status = {}
        try:
            for i in range(len(self.cp_sites_list)):
        
                self.cp_sites_status[str(self.cp_sites_list[i]["id"])] = self.cp_sites_list[i]["admin_state"]
                i +=1
            return self.cp_sites_status

        except TypeError:
            print " Connection Error to the CG API "
            pass

        
    def device_map(self):
        self._cp_elements = cp_sess.get.elements()
        self._cp_elementslist = self._cp_elements.json()['items']
        self.site_element = {}
        for i in range(len(self._cp_elementslist)):
            try:
                self.site_element[self._cp_elementslist[i]['site_id']] = self._cp_elementslist[i]['id']
            except KeyError:
                continue
            i +=1
        return self.site_element


    def site_subnet(self):
        Type1= {'15258453320570225': ['10.64.148.0/24'],'15252075495160109': ['10.64.140.0/24'],'15258455524920079' :['10.64.132.0/24'],'15256733913090257' :['10.65.25.0/24'],
	'15257589990190182' :['10.64.172.0/24'],'15259309497950095' :['10.64.236.0/24'],'15252144469880087' :[],'15263599950740097' :['10.64.100.0/24'],
	'15256731981810129' :['10.64.254.0/24'],'15259311633750131' :['10.64.116.0/24'],'15252077613620147' :['10.64.36.0/24'],'15266257158560187' :['10.64.28.0/24'],
	'15259318725760012' :['10.64.212.0/24'],'15246329007530172' :[],'15263613667500171' :['10.64.228.0/24'],'15239032038550064' :[],'15263598175960134' :['10.64.251.0/24'],
	'15245289965950024' :['10.64.108.0/24'],'15252142864220054' :['10.64.60.0/24'],'15263611487700194' :['10.64.196.0/24'],'15257591583320236' :['10.64.204.0/24'],
        '15286839290380159' :['10.50.12.0/24'],'15295440545610178':['10.134.20.0/24']}
        self.sitesubnet = {}
        
        for k,v in self.site_element.iteritems():

            while len(self.site_element) >= 0:
                try:
                                                          
                    self.sitesubnet[k] = [cp_sess.get.staticroutes(k,v).cgx_content['items'][i]['destination_prefix'] for i in range(len(cp_sess.get.staticroutes(k,v).cgx_content['items']))
                                  if not cp_sess.get.staticroutes(k,v).cgx_content['items'][i]['destination_prefix'].startswith('10.255.') or
                                  cp_sess.get.staticroutes(k,v).cgx_content['items'][i]['destination_prefix'].startswith('10.254.') ]
                except:
                    print "Error"
                    continue
                finally:
                    break
                
            self.sitesubnet.update(Type1)

        return self.sitesubnet


