#!/usr/bin/env python


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sdwanalarms
import schedule
import datetime
import time
import os

'''
Create instance for Sites, Alarms and ID's Class.
'''

s = sdwanalarms.Sites()
al = sdwanalarms.Alarms()
ids = sdwanalarms.Ids()

'''
The getdata function calls the class methods for the above instances created for each class.
The data retrieved from the below method calls are used subsequently for alerting.
'''

def getdata():
    '''
    The getdata function calls the class methods for the above instances created for each class.
    The data retrieved from the below method calls are used subsequently for alerting.
    '''
    s.sitesdata()
    s.sitestatus()

    s.device_map()
    s.site_subnet()

    al.alarmdata()
    al.new_alarms()
    al.curralarm()
    ids.ids()

    print " \n \n Data Refresh Successful \n \n"


'''
This function returns the alarms status. An alarm is run through this function and
output either True or False is used before it can be  reported.
'''

def al_status(corr_id):
    '''
    This function returns the alarms status. An alarm is run through this function and
    output either True or False is used before it can be  reported.
    '''
    
    corr_query = {"limit":{"count":2,"sort_on":"time","sort_order":"descending"},
                                  "view":{"summary":False},"end_time":"","start_time":"","severity":[],
                                  "query":{"site":[],"category":[],"code":[],"correlation_id":[corr_id],"type":["alarm"]}}

    #POST API call to get status of an alarm
    curr_alarm = sdwanalarms.cp_sess.post.events_query(corr_query).cgx_content   

    #Get Value of the field Clear should be , boolean True or False
    curr_alarmstatus = curr_alarm["items"][0]["cleared"]
    
    return curr_alarmstatus


def prefixtosite(prefix):
    '''
    Function that takes a Prefix as an argument and returns the name of the site.
    '''
    
    for i in range(len(s.sitesubnet.values())):
        if prefix in s.sitesubnet.values()[i]:
            sitename = ids.cp_ids[s.sitesubnet.keys()[i]]
            break
        else:
            sitename = 'Piscataway DC'
        i+=1
    return sitename



def skipalarm(alarm):

    if s.cp_sites_status[alarm['site_id']] == 'active':    #The Status of the reporting site should be Active
        if str(alarm['cleared']) ==  'False':              #The alarms should still be Acive 

            if alarm['code'] == 'NETWORK_VPNLINK_DOWN':    #Check for VPN Link Down Alarms
                print "New VPN Alarm"
                if alarm['info']['al_id'] in al.alarmholder:   #Check if the VPN Link 'al_id' is in the al.vpndown bucket.
                    print alarm['info']['al_id'], al.alarmholder     
                    return True                                #Return True is the alarm 'al_id is already in the bucket.
                
                else:                                                                   #The else catches an alarm if the 'al_id' is not in the  al.vpndown bucket.
                    al.alarmholder.append(alarm['info']['al_id'])                           #Add the 'al_id' of the alarm in the bucket.
                    return False


            elif alarm['code'] == 'DEVICEHW_INTERFACE_DOWN':    #Check for interface down alarms.
                if alarm['info']['name'] in ['internet bypass 1', 'wan 2',
                                             'lan 3','wan 3', 'wan 4']:      #Check if the alarm is for "internet bypass or wan 2", you can add any interface which you want to skip.
                    return True                                              # Returns True if the above condition matches so the alarm should be skipped.
                else:                                                        # Returns False if it doesn't and alarm should be considered 
                    return True 
            

            elif alarm['code'] == 'NETWORK_PRIVATEWAN_UNREACHABLE':
                if alarm['info']['prefixes'] in al.alarmholder:
                    return True
                else:
                    al.alarmholder.append(alarm['info']['prefixes'])
                    return False
                                              

            elif alarm['code'] in ['NETWORK_DIRECTINTERNET_DOWN','PEERING_EDGE_DOWN','PEERING_CORE_DOWN',
                                    'DEVICEHW_POWER_LOST','NETWORK_DIRECTPRIVATE_DOWN']:    # Match all other alarm types and return False to Consider this alarm.
                
                return False
            

        else:                       #Matches if the alarm status is 'cleared'. Return True so this alarm will be skipped.
            print 'Alarm Cleared'
            return True
        
    else:                           #Matches if the site status is not 'Active'. Return True so this alarm will be skipped.
        print 'Inactive Site Alarm'
        return True
    

def clear():
    '''  
    Function to clear the al.alarmholder bucket before the alarms are run through the alerting() function.
    This allows any al_id in the bucket is cleared, therefore a new alarm for the same al_id matching
    all conditions does not get skipped.
    '''
    al.alarmholder = []
    print '\n Deleted', al.alarmholder
                           


def alerting():

    '''
    All alarms in the al.n_alarms list are run against this function. If the alarms is eligible to be reported
    it is formatted and sent via e-mail.
    '''
                            
    for i in range(len(al.n_alarms)):
    
        to = ['ucg_wan@colpal.com','miguel_mejia@colpal.com','umesh_shetty@colpal.com']
        message = MIMEMultipart()
        message['From'] = "sdwan_alarms@colpal.com"
        message['To'] = ','.join(to)
        
        try:
            mailconnect = smtplib.SMTP('10.10.10.10', 25) #Enter the IP of your SMTP server and port here.
        except:
            continue


        if al_status(al.n_alarms[i]["correlation_id"]) is False:  

            if skipalarm(al.n_alarms[i]) is False:
                al.alerted.append(al.n_alarms[i])
                
                try:
                    mailconnect = smtplib.SMTP('167.228.1.86', 25)
                except:
                    continue
                
                if  al.n_alarms[i]["code"] == 'NETWORK_VPNLINK_DOWN' and  al.n_alarms[i]["site_id"] == '14976351812410136':

                    message['Subject'] = "%s %s %s OPEN"%(ids.cp_ids[al.n_alarms[i]['info']['al_id']][:ids.cp_ids[al.n_alarms[i]['info']['al_id']].find('(')].rstrip(),
                                                          al.n_alarms[i]["code"], al.n_alarms[i]["severity"])                                       #E-mail subject for alerts

                elif al.n_alarms[i]["code"] == 'NETWORK_PRIVATEWAN_UNREACHABLE':

                    message['Subject'] = "%s %s %s OPEN"%(prefixtosite(al.n_alarms[i]['info']['prefixes']),al.n_alarms[i]["code"], al.n_alarms[i]["severity"])

                else:                                   
                    message['Subject'] = "%s %s %s OPEN"%(ids.cp_ids[al.n_alarms[i]["site_id"]],al.n_alarms[i]["code"], al.n_alarms[i]["severity"]) #E-mail subject for alerts
                  
                #E-mail body of the  Email alert, this can be customized as per requirement.
                msg = """
Event ID           :%s
Event Code         :%s
Site ID            :%s
Site Name          :%s
Device ID          :%s
Device Name        :%s
Correlation ID     :%s
Alarm Time(GMT)    :%s
""" % (al.n_alarms[i]["id"], al.n_alarms[i]["code"], al.n_alarms[i]["site_id"], ids.cp_ids[al.n_alarms[i]["site_id"]], al.n_alarms[i]["element_id"],
       ids.cp_ids[al.n_alarms[i]["element_id"]], al.n_alarms[i]["correlation_id"], datetime.datetime.strptime(al.n_alarms[i]["time"],'%Y-%m-%dT%H:%M:%S.%fZ'))

                msginfo = "\n ALARM INFO:"   #Additional info in the e-mail message.
                alinfo = al.n_alarms[i]['info']  #Picks data from the 'info' part of the alert data
                alkeys = alinfo.keys()    #Stores the keys of the alarm info.

                for i in range(len(alkeys)):

                    if alinfo[alkeys[i]] in ids.cp_ids.keys():
                        #Checks if info key is the cp_id dictionary.

                        msginfo = msginfo + "\n %s = %s" %(alkeys[i], ids.cp_ids[alinfo[alkeys[i]]])  #the id of the value is converted into its name using cp_id dictionary
                    else:
                                                                                                              
                        msginfo = msginfo + "\n %s = %s" %(alkeys[i], alinfo[alkeys[i]]) #else it is used as it is.
                i += 1

                body = msg + msginfo   #Msg info is concantenated to Message
                message.attach(MIMEText(body, 'plain')) 
                text = message.as_string()
                mailconnect.sendmail(message['From'], to, text)

        elif al_status(al.n_alarms[i]["correlation_id"]) is False:

            if al_status(al.n_alarms[i]["correlation_id"]) in alerted:

                    alerted.remove(al_status(al.n_alarms[i]["correlation_id"]))
                        
                    if  al.n_alarms[i]["code"] == 'NETWORK_VPNLINK_DOWN' and  al.n_alarms[i]["site_id"] == '14976351812410136':

                        message['Subject'] = "%s %s %s Resolved"%(ids.cp_ids[al.n_alarms[i]['info']['al_id']][:ids.cp_ids[al.n_alarms[i]['info']['al_id']].find('(')].rstrip(),
                                                              al.n_alarms[i]["code"], al.n_alarms[i]["severity"])                                       #E-mail subject for alerts

                    else:                                   
                        message['Subject'] = "%s %s %s Resolved"%(ids.cp_ids[al.n_alarms[i]["site_id"]],al.n_alarms[i]["code"], al.n_alarms[i]["severity"]) #E-mail subject for alerts

                    msg = """
            Event ID           :%s
            Event Code         :%s
            Site ID            :%s
            Site Name          :%s
            Device ID          :%s
            Device Name        :%s
            Correlation ID     :%s
            Alarm Time(GMT)    :%s
            """ % (al.n_alarms[i]["id"], al.n_alarms[i]["code"], al.n_alarms[i]["site_id"],ids.cp_ids[al.n_alarms[i]["site_id"]],al.n_alarms[i]["element_id"],
                   ids.cp_ids[al.n_alarms[i]["element_id"]], al.n_alarms[i]["correlation_id"],datetime.datetime.strptime(al.n_alarms[i]["time"],'%Y-%m-%dT%H:%M:%S.%fZ'))

                    msginfo = "\n ALARM INFO:"
                    alinfo = al.n_alarms[i]['info']
                    alkeys = alinfo.keys()

                    for i in range(len(alkeys)):
                        if alinfo[alkeys[i]] in ids.cp_ids.keys():                                              
                            msginfo = msginfo + "\n %s = %s" %(alkeys[i], ids.cp_ids[alinfo[alkeys[i]]])
                        else:
                            msginfo = msginfo + "\n %s = %s" %(alkeys[i], alinfo[alkeys[i]])
                        i += 1

                    body = msg + msginfo
                    message.attach(MIMEText(body, 'plain'))
                    text = message.as_string()
                    mailconnect.sendmail(message['From'], to, text)


            else:
                print 'Alarm not reported'

        i+=1
    al.lastalarm_time = al.alarms_list[0]["time"]


def autoalerts():
    '''
    Function that calls other functions that needs to be run periodically to get new alarms info.
    '''                                                           
    if sdwanalarms.cp_sess.tenant_name == 'colpal.com':   #Checks if the tenant in the cache is 'colpal.com', this means the user session is still active

        print "\n  %s Monitoring in progress...Type Ctrl+C to Stop Monitoring  \n\n" %time.ctime()
        alerting()
        al.alarmdata()
        al.new_alarms()

        
    elif sdwanalarms.cp_sess.tenant_name != 'colpal.com': #If tenant is not 'colpal.com' means the session has timedout and needs to reolgin.
        relogin(username, password)

username = "email@company.com"
password = "****************"

'''
Funtion to logout and login to the API.
'''

def relogin():   
    sdwanalarms.cp_sess.interactive.logout()
    print " \n \n Logged Out "
    sdwanalarms.cp_sess.interactive.login(username, password)
    print " \n \n Relogin at", datetime.datetime.now()



schedule.every(8).minutes.do(clear)       #Clear the alarms in the bucket before autoalerts is run, The interval can be set as per the agressiveness of the polling one needs
schedule.every(8).minutes.do(autoalerts)  
schedule.every(120).minutes.do(getdata)    #Fetch data every 120 mins to refresh any new addition. Can be set to a higher interval if no changes are being made in th eenvironment.
schedule.every(350).minutes.do(relogin)   #Logout and Relogin every 350 mins


def monitor():
    while True:
        schedule.run_pending()
        time.sleep(1)


def start(username, password):
    '''
    Function to login to the API using any read credentials.
    '''
    if not sdwanalarms.cp_sess.interactive.login(username,password):
        print "Login failure please try again"
    else:
        print " \n \n Login successful, fetching data..."
        #Fetch Data and start monitor after successful login
        getdata()
        monitor()

#Login once the program is started
start(username, password)




