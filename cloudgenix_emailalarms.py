#!/usr/bin/env python


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sdwanalarms
import schedule
import datetime
import time
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials


#Create instance for Sites, Alarms and ID's Class.

s = sdwanalarms.Sites()
al = sdwanalarms.Alarms()
ids = sdwanalarms.Ids()


scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('Google Project.json',scope)


#The getdata function calls the class methods for the above instances created for each class.
#The data retrieved from the below method calls are used subsequently for alerting.

def getdata():
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
    corr_query = {"limit":{"count":2,"sort_on":"time","sort_order":"descending"},
                                  "view":{"summary":False},"end_time":"","start_time":"","severity":[],
                                  "query":{"site":[],"category":[],"code":[],"correlation_id":[corr_id],"type":["alarm"]}}
    curr_alarm = sdwanalarms.cp_sess.post.events_query(corr_query).cgx_content
    try:
        curr_alarmstatus = curr_alarm["items"][0]["cleared"]
    except TypeError:
        return False
    return curr_alarmstatus



def prefixtosite(prefix):
    '''
    The function takes a prefix as a argument and returns the sitename that prefix belongs to.
    This will be used for idetifying the sitename for 'NETWORK_PRIVATEWAN_UNREACHABLE' alarms
    which only has the prefixes in the info feild and reporting that alarms makes it
    meaningful to add the sitename which is unreachable.
    '''
    for j in range(len(prefix)):

        if not prefix[j].startswith('10.255.'):     #exclude prefixes that are not advertised via both circuits
            if not prefix[j].startswith('10.254.'): #exclude prefixes that are not advertised via both circuits.
             
                for i in range(len(s.sitesubnet.values())):
                 
                    if prefix[j] in s.sitesubnet.values()[i]:
                        
                        sitename = ids.cp_ids[s.sitesubnet.keys()[i]]
                        break
                    else:
                        sitename = 'Piscataway DC'
            i+=1
        j+=1
    return sitename


def skipalarm(alarm):

    if s.cp_sites_status[alarm['site_id']] == 'active':    #The Status of the reporting site should be Active
        if str(alarm['cleared']) ==  'False':              #The alarms should still be Acive 

            if alarm['code'] == 'NETWORK_VPNLINK_DOWN':    #Check for VPN Link Down Alarms
                print "New VPN Alarm"

                if alarm['info']['al_id'] in al.alarmholder:      #Check if the VPN Link 'al_id' is in the al.vpndown bucket.
                    print alarm['info']['al_id'], al.alarmholder     
                    return True                                   #Return True is the alarm 'al_id is already in the bucket.
                                    
                else:                                                                   #The else catches an alarm if the 'al_id' is not in the  al.vpndown bucket.
                    al.alarmholder.append(alarm['info']['al_id'])                       #Add the 'al_id' of the alarm in the bucket.
                    return False
 
            elif alarm['code'] == 'DEVICEHW_INTERFACE_DOWN':    #Check for interface down alarms.
                if alarm['info']['name'] in ['internet bypass 1', 'internet bypass 2',
                                             'wan 2','lan 3','wan 3', 'wan 4']:      #Check if the alarm is for "internet bypass or wan 2", you can add any interface which you want to skip.
                    return True                                              # Returns True if the above condition matches so the alarm should be skipped.
                else:                                                        # Returns False if it doesn't and alarm should be considered 
                    return False 
            
            elif alarm['code'] == 'NETWORK_PRIVATEWAN_UNREACHABLE':
                if alarm['info']['prefixes'] in al.alarmholder:
                    return True
                else:
                    al.alarmholder.append(alarm['info']['prefixes'])
                    return False

            elif alarm['code'] in ['NETWORK_DIRECTINTERNET_DOWN','PEERING_EDGE_DOWN','PEERING_CORE_DOWN',
                                    'DEVICEHW_POWER_LOST','NETWORK_DIRECTPRIVATE_DOWN']:    # Match all other alarm types and return False to Consider this alarm.
                
                return False

            elif alarm['code'] in ['DEVICEHW_DISKUTIL_PARTITIONSPACE','DEVICEHW_MEMUTIL_SWAPSPACE','DEVICEHW_DISKENC_SYSTEM','DEVICEIF_ADDRESS_DUPLICATE',
                                    'DEVICESW_GENERAL_PROCESSRESTART','DEVICESW_GENERAL_PROCESSSTOP','DEVICESW_MONITOR_DISABLED','DEVICESW_GENERAL_PROCESSRESTART',
                                    'DEVICESW_IMAGE_UNSUPPORTED','DEVICEHW_INTERFACE_HALFDUPLEX','DEVICESW_FPS_LIMIT_EXCEEDED','DEVICESW_CONCURRENT_FLOWLIMIT_EXCEEDED',
                                    'DEVICESW_LICENSE_VERIFICATION_FAILED','DEVICESW_TOKEN_VERIFICATION_FAILED','VPNLINK_CIPHERS_INCOMPATIBLE','APPLICATION_IP_COLLISION',
                                    'APPLICATION_FLOWCTRL_APPUNREACHABLE','OPERATOR_SIGNUP_TOKEN_DISABLED']:
                return False


                        
        elif str(alarm['cleared']) ==  'True' and  alarm['code'] in ['DEVICEHW_DISKUTIL_PARTITIONSPACE','DEVICEHW_MEMUTIL_SWAPSPACE','DEVICEHW_DISKENC_SYSTEM','DEVICEIF_ADDRESS_DUPLICATE',
                                    'DEVICESW_GENERAL_PROCESSRESTART','DEVICESW_GENERAL_PROCESSSTOP','DEVICESW_MONITOR_DISABLED','DEVICESW_GENERAL_PROCESSRESTART',
                                    'DEVICESW_IMAGE_UNSUPPORTED','DEVICEHW_INTERFACE_HALFDUPLEX','DEVICESW_FPS_LIMIT_EXCEEDED','DEVICESW_CONCURRENT_FLOWLIMIT_EXCEEDED',
                                    'DEVICESW_LICENSE_VERIFICATION_FAILED','DEVICESW_TOKEN_VERIFICATION_FAILED','VPNLINK_CIPHERS_INCOMPATIBLE','APPLICATION_IP_COLLISION',
                                    'APPLICATION_FLOWCTRL_APPUNREACHABLE','OPERATOR_SIGNUP_TOKEN_DISABLED']:
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
    try:
        al.alarmholder = []
        print '\n Deleted', al.alarmholder
    except Exception as e:
        print e


def alerting():
    '''
    All alarms in the al.n_alarms list are run against this function. If the alarms is eligible to be reported
    it is formatted and sent via e-mail.
    '''
                           
    for i in range(len(al.n_alarms)):

        to = ['email@company.com']
        message = MIMEMultipart()
        message['From'] = "sdwan_test@colpal.com" #You can change this to the email ID of your choice.
        message['To'] = ','.join(to)

        sitename = ""
        code = ""
        sheet_insert = []
        
        if al_status(al.n_alarms[i]["correlation_id"]) is False:  

            if skipalarm(al.n_alarms[i]) is False:
                al.alerted.append(al.n_alarms[i])
                               
                try:
                    mailconnect = smtplib.SMTP('10.10.10.10', 25) #Change this to the IP address of your SMTP server.
                except:
                    continue
                
                if  al.n_alarms[i]["code"] == 'NETWORK_VPNLINK_DOWN' and  al.n_alarms[i]["site_id"] == '14976351812410136':
                    sitename = ids.cp_ids[al.n_alarms[i]['info']['al_id']][:ids.cp_ids[al.n_alarms[i]['info']['al_id']].find('(')].rstrip()
                    code = 'VPN Down'
                    message['Subject'] = "%s - %s - %s- OPEN"%(sitename, code,al.n_alarms[i]["severity"])                                #E-mail subject for alerts
                     

                elif  al.n_alarms[i]["code"] == 'NETWORK_VPNLINK_DOWN':
                    sitename = ids.cp_ids[al.n_alarms[i]["site_id"]]
                    code = 'VPN Down'
                    message['Subject'] = "%s - %s - %s- OPEN"%(sitename,code, al.n_alarms[i]["severity"])       #E-mail subject for alerts

                elif  al.n_alarms[i]["code"] == 'NETWORK_DIRECTPRIVATE_DOWN':
                    sitename = ids.cp_ids[al.n_alarms[i]["site_id"]]
                    code = 'MPLS BFD DOWN'
                    message['Subject'] = "%s - %s - %s- OPEN"%(sitename,code, al.n_alarms[i]["severity"])       #E-mail subject for alerts

                elif al.n_alarms[i]["code"] == 'NETWORK_PRIVATEWAN_UNREACHABLE':
                    sitename = prefixtosite(al.n_alarms[i]['info']['prefixes'])
                    code = 'MPLS Link Down'
                    message['Subject'] = "%s - %s - %s - OPEN"%(sitename, code, al.n_alarms[i]["severity"])

                elif al.n_alarms[i]["code"] == 'NETWORK_DIRECTINTERNET_DOWN':
                    sitename = ids.cp_ids[al.n_alarms[i]["site_id"]]
                    code = 'Direct Internet Down'
                    message['Subject'] = "%s - %s - %s - OPEN"%(sitename, code,al.n_alarms[i]["severity"]) #E-mail subject for alerts

                else:
                    sitename = ids.cp_ids[al.n_alarms[i]["site_id"]]
                    code = al.n_alarms[i]["code"]
                    message['Subject'] = "%s - %s - %s - OPEN"%(sitename,code, al.n_alarms[i]["severity"]) #E-mail subject for alerts


                cur_time = time.localtime()
                time_now = float(str(cur_time.tm_hour) +'.'+str(cur_time.tm_min))


                    
                corr_id = al.n_alarms[i]["correlation_id"]
                dev_name = ids.cp_ids[(al.n_alarms[i]["element_id"])]
                al_time = al.n_alarms[i]["time"].rstrip('Z')
                
                #E-mail body of the  Email alert, this can be customized as per requirement.
                msg = """
Event ID           :%s
Event Code         :%s
Site ID            :%s
Site Name          :%s
Reporting Dev      :%s
Correlation ID     :%s
Alarm Time(GMT)    :%s
""" % (al.n_alarms[i]["id"], code, al.n_alarms[i]["site_id"],sitename,dev_name,corr_id,al_time)

                
                msginfo = "\n ALARM INFO:"       #Additional info in the e-mail message.
                alinfo = al.n_alarms[i]['info']  #Picks data from the 'info' part of the alert data
                alkeys = alinfo.keys()           #Stores the keys of the alarm info.

                for i in range(len(alkeys)):

                    if alinfo[alkeys[i]] in ids.cp_ids.keys():  #Checks if info key is the cp_id dictionary.
                        msginfo = msginfo + "\n %s = %s" %(alkeys[i], ids.cp_ids[alinfo[alkeys[i]]])  #the id of the value is converted into its name using cp_id dictionary
                                                           
                    else:
                        msginfo = msginfo + "\n %s = %s" %(alkeys[i], alinfo[alkeys[i]]) #else it is used as it is.
                i += 1


                body = msg + msginfo                              #Msg info is concantenated to Message
                message.attach(MIMEText(body, 'plain')) 
                text = message.as_string()
                mailconnect.sendmail(message['From'], to, text)

                print "\n  Email Sent"
                
                if time_now >= 8.30 and sitename in indiawh:
                    print "\n India WH Shutdown Not reported"
                    pass
                else:
                    
                    sheet_insert = [corr_id,sitename,dev_name,al_time,code,msginfo]
                    client = gspread.authorize(creds)
                    sheet = client.open('SDWAN ALARMS').sheet1
                    sheet.append_row(sheet_insert)
                    "\n Non India Alarm Reported"

            else:
                print 'Alarm not reported'

        i+=1
    al.lastalarm_time = al.alarms_list[0]["time"]


def alarmupdates():
    print "\n Alarmupdate Function Started "
    
    client = gspread.authorize(creds)
    sheet = client.open('SDWAN ALARMS').sheet1 #Name of your Google Sheets
    rowsize = sheet.row_count
    open_corr = []


    for i in range(2,rowsize):
        try:
            open_corr.append(sheet.cell(i+1,1).value)
        except:
            continue
        i+=1

    for j in range(len(open_corr)):
        try:
            if al_status(open_corr[j]) is True:
                sheet.delete_row(sheet.find(open_corr[j]).row)
        except Exception as e:
            print e
            continue
        j+=1
    print "\n Alarmupdate Completed"
    

f = open('C:\Python27\ST.txt') #Path for your Token
token = f.read()


def autoalerts():
    '''
    Function that calls other functions that needs to be run periodically to get new alarms info.
    '''                                                           
    if sdwanalarms.cp_sess.tenant_name == 'colpal.com':   #Checks if the tenant in the cache is 'colpal.com', this means the user session is still active
                    
        print "\n  %s Monitoring in progress...Type Ctrl+C to Stop Monitoring  \n\n" %time.ctime()
        alerting()
        al.alarmdata()
        al.new_alarms()
        

    elif sdwanalarms.cp_sess.tenant_name != 'company.com': #If tenant is not 'company.com' means the session has timedout and needs to reolgin.Change this to your company domain.
        start(token)


schedule.every(8).minutes.do(clear)
schedule.every(8).minutes.do(autoalerts)
schedule.every(8).minutes.do(alarmupdates)
schedule.every(240).minutes.do(getdata)


def monitor():
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            print e
            print " \n Error encountered, continuing \n"
            start(token)


def start(token):
    if not sdwanalarms.cp_sess.interactive.use_token(token):
        print "Login failure please try again"
    else:
        print " \n \n Login successful, fetching data..."
        getdata()
        monitor()

start(token)

