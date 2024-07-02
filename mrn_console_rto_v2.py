# |-----------------------------------------------------------------------------
# |            This source code is provided under the Apache 2.0 license      --
# |  and is provided AS IS with no warranty or guarantee of fit for purpose.  --
# |                See the project's LICENSE.md for details.                  --
# |           Copyright LSEG 2024. All rights reserved.                       --
# |-----------------------------------------------------------------------------


#!/usr/bin/env python
import os
import sys
import time
import getopt
import socket
import json
import threading
from datetime import datetime
import base64
import zlib
import requests
import websocket
from dotenv import load_dotenv

# Global Default Variables
app_id = '256'
auth_token = ''
expire_time = ''
auth_url = 'https://api.refinitiv.com/auth/oauth2/v2/token'
clientid = ''
client_secret = ''
discovery_url = 'https://api.refinitiv.com/streaming/pricing/v1/'
hostName = ''
hostList = []
backupHostList = []
port = 443
position = ''
region = 'ap-southeast-1'
ric = '/TRI.N'
scope = 'trapi.streaming.pricing.read'
service = 'ELEKTRON_DD'
curTS = 0
tokenTS = 0

mrn_domain = 'NewsTextAnalytics'
mrn_item = 'MRN_STORY'
_news_envelopes = []



class WebSocketSession:
    ''' Class for manage WebSocket connection '''
    session_name = ''
    web_socket_app = None
    web_socket_open = False
    host = ''
    force_disconnected = False
    reconnecting = True
    wst = None 

    def __init__(self, name, host):
        self.session_name = name
        self.host = host

    # --------------------MRN Process Code --------------------------------- #
    def decode_fieldlist(self, fieldlist_dict):
        """Function iterates and decodes fieldlist object"""
        for key, value in fieldlist_dict.items():
            print(f'Name = {key}: Value = {value}')


    def send_mrn_request(self):
        """ Create and send MRN request """
        mrn_req_json = {
            'ID': 2,
            'Domain': mrn_domain,
            'Key': {
                'Name': mrn_item,
                'Service': service
            }
        }

        self.web_socket_app.send(json.dumps(mrn_req_json))
        print('SENT:')
        print(json.dumps(mrn_req_json, sort_keys=True, indent=2, separators=(',', ':')))

    def process_refresh(self, message_json):
        """Function process Refresh message"""
        print('RECEIVED: Refresh Message')
        self.decode_fieldlist(message_json['Fields'])

    def process_mrn_update(self, message_json):  
        """Function process Update Message for MRN domain data"""
        fields_data = message_json['Fields']
        # Dump the FieldList first (for informational purposes)
        # self.decode_fieldlist(message_json["Fields"])

        # declare variables
        tot_size = 0
        guid = None

        try:
            # Get data for all required fields
            fragment = base64.b64decode(fields_data['FRAGMENT'])
            frag_num = int(fields_data['FRAG_NUM'])
            guid = fields_data['GUID']
            mrn_src = fields_data['MRN_SRC']

            #print("GUID  = %s" % guid)
            #print("FRAG_NUM = %d" % frag_num)
            #print("MRN_SRC = %s" % mrn_src)

            if frag_num > 1:  # We are now processing more than one part of an envelope - retrieve the current details
                guid_index = next((index for (index, d) in enumerate(_news_envelopes) if d['GUID'] == guid), None)
                envelop = _news_envelopes[guid_index]
                if envelop and envelop['data']['MRN_SRC'] == mrn_src and frag_num == envelop['data']['FRAG_NUM'] + 1:
                    print(f'process multiple fragments for guid {envelop["GUID"]}')

                    #print(f'fragment before merge = {len(envelop["data"]["FRAGMENT"])}')
                    # Merge incoming data to existing news envelop and getting FRAGMENT and TOT_SIZE data to local variables
                    fragment = envelop['data']['FRAGMENT'] = envelop['data']['FRAGMENT'] + fragment
                    envelop['data']['FRAG_NUM'] = frag_num
                    tot_size = envelop['data']['tot_size']
                    print(f'TOT_SIZE = {tot_size}')
                    print(f'Current FRAGMENT length = {len(fragment)}')

                    # The multiple fragments news are not completed, waiting.
                    if tot_size != len(fragment):
                        return None
                    # The multiple fragments news are completed, delete associate GUID envelop
                    elif tot_size == len(fragment):
                        del _news_envelopes[guid_index]
                else:
                    print(f'Error: Cannot find fragment for GUID {guid} with matching FRAG_NUM or MRN_SRC {mrn_src}')
                    return None
            else:  # FRAG_NUM = 1 The first fragment
                tot_size = int(fields_data['TOT_SIZE'])
                print(f'FRAGMENT length = {len(fragment)}')
                # The fragment news is not completed, waiting and add this news data to envelop object.
                if tot_size != len(fragment):
                    print(f'Add new fragments to news envelop for guid {guid}')
                    _news_envelopes.append({  # the envelop object is a Python dictionary with GUID as a key and other fields are data
                        'GUID': guid,
                        'data': {
                            'FRAGMENT': fragment,
                            'MRN_SRC': mrn_src,
                            'FRAG_NUM': frag_num,
                            "tot_size": tot_size
                        }
                    })
                    return None

            # News Fragment(s) completed, decompress and print data as JSON to console
            if tot_size == len(fragment):
                print(f'decompress News FRAGMENT(s) for GUID {guid}')
                decompressed_data = zlib.decompress(fragment, zlib.MAX_WBITS | 32)
                print(f'News = {json.loads(decompressed_data)}')

        except KeyError as keyerror:
            print('KeyError exception: ', keyerror)
        except IndexError as indexerror:
            print('IndexError exception: ', indexerror)
        except binascii.Error as b64error:
            print('base64 decoding exception:', b64error)
        except zlib.error as error:
            print('zlib decompressing exception: ', error)
        # Some console environments like Windows may encounter this unicode display as a limitation of OS
        except UnicodeEncodeError as encodeerror:
            print(f'UnicodeEncodeError exception. Cannot decode unicode character for {guid} in this environment: ', encodeerror)
        except Exception as e:
            print('exception: ', sys.exc_info()[0])


    def process_status(self, message_json):  # process incoming status message
        """Function process incoming status message"""
        print('RECEIVED: Status Message')
        print(json.dumps(message_json, sort_keys=True, indent=2, separators=(',', ':')))

    # ---JSON-OMM Process functions ---#
    def _send_login_request(self, authn_token):
        """
            Send login request with authentication token.
            Used both for the initial login and subsequent reissues to update the authentication token
        """
        login_json = {
            'ID': 1,
            'Domain': 'Login',
            'Key': {
                'NameType': 'AuthnToken',
                'Elements': {
                    'ApplicationId': '',
                    'Position': '',
                    'AuthenticationToken': ''
                }
            }
        }

        login_json['Key']['Elements']['ApplicationId'] = app_id
        login_json['Key']['Elements']['Position'] = position
        login_json['Key']['Elements']['AuthenticationToken'] = authn_token

        self.web_socket_app.send(json.dumps(login_json))
        print(str(datetime.now()) + " SENT on " + self.session_name + ":")
        print(json.dumps(login_json, sort_keys=True, indent=2, separators=(',', ':')))

    def _process_login_response(self, message_json):
        """ Send item request upon login success """
        if message_json['Type'] == "Status" and message_json['Domain'] == "Login" and \
                (message_json['State']['Stream'] != "Open" or message_json['State']['Data'] != "Ok"):
            print(f'{str(datetime.now())} Error: Login failed, received status message, closing: StreamState={message_json["State"]["Stream"]}, DataState={message_json["State"]["Data"]}')
            if self.web_socket_open:
                self.web_socket_app.close()
            self.force_disconnected = True
            return

        #self._send_market_price_request(ric)
        self.send_mrn_request()

    def _process_message(self, message_json):
        """ Parse at high level and output JSON of message """
        message_type = message_json['Type']
        
        if message_type == 'Refresh':
            if 'Domain' in message_json:
                message_domain = message_json['Domain']
                if message_domain == 'Login':
                    self._process_login_response(message_json)
                elif message_domain:
                    self.process_refresh(message_json)
        elif message_type == 'Update':
            if 'Domain' in message_json and message_json['Domain'] == mrn_domain:
                self.process_mrn_update(message_json)
        elif message_type == 'Status':
            self.process_status(message_json)
        elif message_type == 'Ping':
            pong_json = {'Type': 'Pong'}
            self.web_socket_app.send(json.dumps(pong_json))
            #print(str(datetime.now()) + " SENT on " + self.session_name + ":")
            print(f'{str(datetime.now())} SENT on {self.session_name}:')
            print(json.dumps(pong_json, sort_keys=True, indent=2, separators=(',', ':')))

    # Callback events from WebSocketApp
    def _on_message(self, ws, message):
        """ Called when message received, parse message into JSON for processing """
        #print(str(datetime.now()) + " RECEIVED on " + self.session_name + ":")
        print(f'{str(datetime.now())} RECEIVED on {self.session_name}:')
        message_json = json.loads(message)
        print(json.dumps(message_json, sort_keys=True, indent=2, separators=(',', ':')))

        for single_msg in message_json:
            self._process_message(single_msg)

    def _on_error(self, ws, error):
        """ Called when websocket error has occurred """
        #print(str(datetime.now()) + " " + str(self.session_name) + ": Error: "+ str(error))
        print(f'{str(datetime.now())} {str(self.session_name)}: Error {str(error)}')

    def _on_close(self, ws, close_status_code, close_message):
        """ Called when websocket is closed """
        self.web_socket_open = False
        #print(str(datetime.now()) + " " + str(self.session_name) + ": WebSocket Closed\n")
        print(f'{str(datetime.now())} {str(self.session_name)}: WebSocket Closed\n')

    def _on_open(self, ws):
        """ Called when handshake is complete and websocket is open, send login """

        #print(str(datetime.now()) + " " + str(self.session_name) + ": WebSocket successfully connected!")
        print(f'{str(datetime.now())} {str(self.session_name)}: WebSocket successfully connected!')
        self.web_socket_open = True
        self.reconnecting = False
        self._send_login_request(auth_token)

    # Operations
    def connect(self):
        ''' Connect to RTO WebSocket '''
        # Start websocket handshake
        ws_address = f'wss://{self.host}/WebSocket'
        #websocket.enableTrace(True)
        if (not self.web_socket_app) or self.reconnecting:
            self.web_socket_app = websocket.WebSocketApp(ws_address, 
                                                     on_message=self._on_message,
                                                     on_error=self._on_error,
                                                     on_close=self._on_close,
                                                     on_open=self._on_open,
                                                     subprotocols=['tr_json2'])
        # Event loop
        if not self.wst:
            print(f'{str(datetime.now())} {str(self.session_name)}: Connecting WebSocket to {ws_address} ...')
            self.wst = threading.Thread(target=self.web_socket_app.run_forever, kwargs={'sslopt': {'check_hostname': False}})
            self.wst.daemon = True
            self.wst.start()
        elif self.reconnecting and not self.force_disconnected:
            print(f'{str(datetime.now())} {str(self.session_name)}: Reconnecting WebSocket to {ws_address} ...')
            self.web_socket_app.run_forever()


    def disconnect(self):
        """Function disconnect the WebSocket connection"""
        self.force_disconnected = True
        if self.web_socket_open:
            print(str(datetime.now()) + " " + self.session_name + ": Closing WebSocket\n")
            self.web_socket_app.close()


def query_service_discovery(url=None):
    """
        Retrieves list of endpoints.
    """
    if url is None:
        url = discovery_url

    print(f'\n{str(datetime.now())}Sending Delivery Platform service discovery request to {url}...\n')
    try:
        r = requests.get(url, 
                         headers={'Authorization': f'Bearer {auth_token}'}, 
                         params={'transport': 'websocket'}, 
                         allow_redirects=False , timeout= 45)

    except requests.exceptions.RequestException as e:
        print('Delivery Platform service discovery exception failure:', e)
        return False

    if r.status_code == 200:
        # Authentication was successful. Deserialize the response.
        response_json = r.json()
        print(str(datetime.now()) + " Delivery Platform Service discovery succeeded." + \
                " RECEIVED:")
        print(json.dumps(response_json, sort_keys=True, indent=2, separators=(',', ':')))

        for index in range(len(response_json['services'])):
            if not response_json['services'][index]['location'][0].startswith(region):
                continue


            if len(response_json['services'][index]['location']) >= 2:
                hostList.append(response_json['services'][index]['endpoint'] + ":" +
                                str(response_json['services'][index]['port']))
                continue
            if len(response_json['services'][index]['location']) == 1:
                backupHostList.append(response_json['services'][index]['endpoint'] + ":" +
                                str(response_json['services'][index]['port']))
                continue


        if len(hostList) == 0:
            if len(backupHostList) > 0:
                for hostIndex in range(len(backupHostList)):
                    hostList.append(backupHostList[hostIndex])
            else:
                print(f'The region: {region} is not present in list of endpoints')
                sys.exit(1)

        return True

    elif r.status_code in [ 301, 302, 307, 308 ]:
        # Perform URL redirect
        print('Delivery Platform service discovery HTTP code:', r.status_code, r.reason)
        new_host = r.headers['Location']
        if new_host != None:
            print('Perform URL redirect to ', new_host)
            return query_service_discovery(new_host)
        return False
    elif r.status_code in [ 403, 404, 410, 451 ]:
        # Stop trying the request
        print('Delivery Platform service discovery HTTP code:', r.status_code, r.reason)
        print('Unrecoverable error when performing service discovery: stopped retrying request')
        return False
    else:
        # Retry request with an appropriate delay: 
        print('Delivery Platform service discovery HTTP code:', r.status_code, r.reason)
        time.sleep(5)
        # CAUTION: This is sample code with infinite retries.
        print('Retrying the service discovery request')
        return query_service_discovery()


def get_auth_token(url=None):
    """
        Retrieves an authentication token.
    """

    if url is None:
        url = auth_url

    data = {'grant_type': 'client_credentials', 'scope': scope, 'client_id': clientid, 'client_secret': client_secret}

    print(f'\n{str(datetime.now())}Sending authentication request with client credentials to {url} ...\n')
    try:
        # Request with auth for https protocol    
        r = requests.post(url,
                headers={'Accept' : 'application/json'},
                          data=data,
                          verify=True,
                          allow_redirects=False, timeout= 45)

    except requests.exceptions.RequestException as e:
        print('Delivery Platform authentication exception failure:', e)
        return None, None

    if r.status_code == 200:
        auth_json = r.json()
        print(f'{str(datetime.now())} Delivery Platform Authentication succeeded. RECEIVED:')
        print(json.dumps(auth_json, sort_keys=True, indent=2, separators=(',', ':')))
        return auth_json['access_token'], auth_json['expires_in']
    elif r.status_code in [ 301, 302, 307, 308 ]:
        # Perform URL redirect
        print('Delivery Platform authentication HTTP code:', r.status_code, r.reason)
        new_host = r.headers['Location']
        if new_host != None:
            print('Perform URL redirect to ', new_host)
            return get_auth_token(new_host)
        return None, None
    elif r.status_code in [ 400, 401, 403, 404, 410, 451 ]:
        # Stop trying the request
        # NOTE: With 400 and 401, there is not retry to keep this sample code simple
        print('Delivery Platform authentication HTTP code:', r.status_code, r.reason)
        print('Unrecoverable error: stopped retrying request')
        return None, None
    else:
        print('Delivery Platform authentication failed. HTTP code:', r.status_code, r.reason)
        time.sleep(5)
        # CAUTION: This is sample code with infinite retries.
        print('Retrying auth request')
        return get_auth_token()


def print_commandline_usage_and_exit(exit_code):
    print('Usage: market_price_rdpgw_client_cred_auth.py [--app_id app_id] '
          '--clientid clientid --clientsecret client secret [--position position] [--auth_url auth_url] '
          '[--hostname hostname] [--port port] ' 
          '[--discovery_url discovery_url] [--scope scope] [--service service]'
          '[--region region] [--ric ric] [--help]')
    sys.exit(exit_code)


if __name__ == "__main__":
    # Get config from Environment Variable

    load_dotenv()  # take environment variables from .env.
    clientid = os.environ['CLIENT_ID']
    client_secret = os.environ['CLIENT_SECRET']
    # Get command line parameters
    opts = []
    try:
        opts, args = getopt.getopt(sys.argv[1:], "", [
            "help", "app_id=", "clientsecret=", "clientid=", 
            "hostname=", "port=", 
            "position=", "auth_url=", "discovery_url=", 
            "scope=", "service=", "region=", "ric="])
    except getopt.GetoptError:
        print_commandline_usage_and_exit(2)
    for opt, arg in opts:
        if opt in "--help":
            print_commandline_usage_and_exit(0)
        elif opt in "--app_id":
            app_id = arg
        elif opt in "--clientsecret":
            client_secret = arg
        elif opt in "--clientid":
            clientid = arg
        elif opt in "--hostname":
            hostName = arg
        elif opt in "--port":
            port = arg
        elif opt in "--position":
            position = arg
        elif opt in "--service":
            service = arg
        elif opt in "--region":
            region = arg
        elif opt in "--ric":
            if arg not in ['MRN_STORY', 'MRN_TRNA', 'MRN_TRNA_DOC', 'MRN_TRSI']:
                print('The supported MRN RIC names are MRN_STORY or MRN_TRNA or MRN_TRNA_DOC or MRN_TRSI only')
                sys.exit(2)
            else:
                mrn_item = arg

    if clientid == '' or client_secret == '':
        print('Authentication Version 2 clientid and clientsecret are required options')
        sys.exit(2)
        
    if position == '':
        # Populate position if possible
        try:
            position_host = socket.gethostname()
            position = f'{socket.gethostbyname(position_host)}/{position_host}'
        except socket.gaierror:
            position = '127.0.0.1/net'

    auth_token, expire_time = get_auth_token()
    if not auth_token:
        print('Failed initial authentication with Delivery Platform. Exiting...')
        sys.exit(1)
    # get an access token receiving time, used for connection logic
    tokenTS = time.time() 

    # If hostname is specified, use it for the connection
    if hostName != '':
        hostList.append(f'{hostName}:{str(port)}')
    else:
        # Query VIPs from Delivery Platform service discovery if user did not specify hostname
        if not query_service_discovery():
            print('Failed to retrieve endpoints from Delivery Platform Service Discovery. Exiting...')
            sys.exit(1)

    # Start websocket handshake;
    session1 = WebSocketSession('Session1', hostList[0])
    session1.connect()

    try:
        while True:
            # NOTE about connection recovery: When connecting or reconnecting 
            #   to the server, a valid token must be used. Upon being disconnecting, initial 
            #   reconnect attempt must be done with  a new token.
            #   If a successful reconnect takes longer than token expiration time, 
            #   a new token must be obtained proactively. 

            # Waiting a few seconds before checking for connection down and attempting reconnect
            time.sleep(5)
            if not session1.web_socket_open:
                if session1.reconnecting:
                    curTS = time.time()
                    if (int(expire_time) < 600):
                        DELTA_TIME = float(expire_time) * 0.05
                    else:
                        DELTA_TIME = 300
                    if (int(curTS) >= int(float(tokenTS) + float(expire_time) - float(DELTA_TIME))):
                        auth_token, expire_time = get_auth_token() 
                        tokenTS = time.time()
                else:
                    auth_token, expire_time = get_auth_token() 
                    tokenTS = time.time()

                if not session1.web_socket_open and not session1.force_disconnected:
                    session1.reconnecting = True

                if auth_token is not None:
                    if (not session1.force_disconnected) and session1.reconnecting:
                        session1.connect()
                else:
                    print('Failed authentication with Delivery Platform. Exiting...')
                    sys.exit(1) 


    except KeyboardInterrupt:
        session1.disconnect()