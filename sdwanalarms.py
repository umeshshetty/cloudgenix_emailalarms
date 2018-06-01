#!/usr/bin/env python

"""
Python2.7 Module for Interaction with the Cloudgenix API.

**Version:** v1.0


#### Synopsis
Intended to be used for Colgate to use the Cloudgenix API for report events via e-mail.
Usage of this module requires knwoledge of Python2.7 and using standard libraries like e-mail and scheduler.

"""

__author__ = "Umesh Shetty"
__email__ = "umesh_shetty@colpal.com"
__status__ = "Development"


# Import CloudGenix SDK
import cloudgenix

# Import CloudGenix json, smtplib, datetime, cloudgenix_idname
import json
import smtplib
import datetime
import cloudgenix_idname
    

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
            

end_time = datetime.datetime.isoformat(datetime.datetime.utcnow())
start_time = datetime.datetime.isoformat(datetime.datetime.utcnow()- datetime.timedelta(hours=2))

class Alarms(object):
    """
    Class method to query the Cloudgenix API for the Alarms in the system
    """

    def __init__(self):
        self.lastalarm_time = datetime.datetime.isoformat(datetime.datetime.utcnow())

        """
        At class initialization sets the time to current time in UTC. This counter will
        change during execution of other methods in the class and help if returning
        new Alarms.
        """

    def alarmdata(self):
        """
        Class method to collect alarmdata
        """
        
        self.query_data = {"limit":{"count":25,"sort_on":"time","sort_order":"descending"},"view":{"summary":False},"end_time":"",
                           "start_time":"","severity":[],"query":{"site":[],"category":[],
                            "code":['NETWORK_DIRECTINTERNET_DOWN','PEERING_EDGE_DOWN','PEERING_CORE_DOWN', 
                                    'DEVICEHW_POWER_LOST','DEVICEHW_INTERFACE_DOWN','NETWORK_PRIVATEWAN_UNREACHABLE','NETWORK_DIRECTPRIVATE_DOWN']
                                    ,"correlation_id":[],"type":["alarm"]}}

        self.alarms = json.loads(json.dumps(cp_sess.post.events_query(self.query_data).cgx_content, indent = 4)) #Returns all alarms and stores in the variable

        try:
            self.alarms_list = self.alarms["items"] #Extracts all alarms from the Alarmdata and stores it in a List of alarms

        except KeyError:
            print " Connection Error to the CG API "

        return self.alarms_list
      
  

    def new_alarms(self):
        """
        Class method to identify new alarm from the alarm list using the lastalarmtime as the delta.
        """
   
        self.n_alarms = [] #sets the new alarms list as empty list at initiation
        
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

        self.cp_sitesraw = json.loads(json.dumps(cp_sess.get.sites().cgx_content, indent = 4 ))
        """
        Variable to store the raw sites data
        """

        self.cp_sites_list = self.cp_sitesraw["items"]
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

        
    def device_map(self):
        self.cp_elements = cp_sess.get.elements()
        self.cp_elementslist = self.cp_elements.json()['items']
        self.site_element = {}
        for i in range(len(self.cp_elementslist)):
            try:
                self.site_element[self.cp_elementslist[i]['site_id']] = self.cp_elementslist[i]['id']
            except KeyError:
                continue
            i +=1
        return self.site_element


    def site_subnet(self):
        self.sitesubnet = {}
        
        for k,v in self.site_element.iteritems():
                  
            self.sitesubnet[k] = [cp_sess.get.staticroutes(k,v).cgx_content['items'][i]['destination_prefix'] for i in range(len(cp_sess.get.staticroutes(k,v).cgx_content['items']))]

        return self.sitesubnet


