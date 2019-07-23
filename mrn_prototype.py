# |-----------------------------------------------------------------------------
# |            This source code is provided under the Apache 2.0 license      --
# |  and is provided AS IS with no warranty or guarantee of fit for purpose.  --
# |                See the project's LICENSE.md for details.                  --
# |           Copyright Thomson Reuters 2017. All rights reserved.            --
# |-----------------------------------------------------------------------------


#!/usr/bin/env python
""" Simple example of outputting Market Price JSON data using Websockets """

import sys
import time
import getopt
import socket
import json
import websocket
import threading
from threading import Thread, Event
import base64
import zlib

# Global Default Variables
hostname = '172.20.33.30'
port = '15000'
user = 'root'
app_id = '256'
position = socket.gethostbyname(socket.gethostname())
mrn_domain = 'NewsTextAnalytics'
mrn_item = 'MRN_STORY'

# Global Variables
web_socket_app = None
web_socket_open = False

_news_envelopes = []

''' MRN Process Code '''


def decodeFieldList(fieldList_dict):
    for key, value in fieldList_dict.items():
        print("Name = %s: Value = %s" % (key, value))


def send_mrn_request(ws):
    """ Create and send MRN request """
    mrn_req_json = {
        'ID': 2,
        'Domain': mrn_domain,
        'Key': {
            'Name': mrn_item
        }
    }

    ws.send(json.dumps(mrn_req_json))
    print("SENT:")
    print(json.dumps(mrn_req_json, sort_keys=True, indent=2, separators=(',', ':')))


def processRefresh(ws, message_json):

    print("RECEIVED: Refresh Message")
    decodeFieldList(message_json["Fields"])


def parseNewsData(fragment):
    decompressed_data = zlib.decompress(fragment, zlib.MAX_WBITS | 32)
    print("News = %s" % decompressed_data)


def processUpdate(ws, message_json):
    print("RECEIVED: Update Message")
    # print(message_json)

    fields_data = message_json["Fields"]
    # Dump the FieldList first (for informational purposes)
    decodeFieldList(message_json["Fields"])

    try:
        # Get data for all requried fields
        fragment = base64.b64decode(fields_data["FRAGMENT"])
        frag_num = int(fields_data["FRAG_NUM"])
        guid = fields_data["GUID"]
        mrn_src = fields_data["MRN_SRC"]

        print("GUID  = %s" % guid)
        print("FRAG_NUM = %d" % frag_num)
        print("MRN_SRC = %s" % mrn_src)

        #fragment_decoded = base64.b64decode(fragment)
        print("fragment length = %d" % len(fragment))
        if frag_num > 1:  # We are now processing more than one part of an envelope - retrieve the current details
            guid_index = next((index for (index, d) in enumerate(
                _news_envelopes) if d["guid"] == guid), None)
            envelop = _news_envelopes[guid_index]
            if envelop:
                print("process multiple fragments for guid %s" %
                      envelop["guid"])
                # print(envelop)
                #print("fragment before merge = %d" % len(envelop["data"]["fragment"]))

                # Merge incoming fragment to current fragment
                envelop["data"]["fragment"] = envelop["data"]["fragment"] + fragment

                #print("TOT_SIZE from envelop = %d" % envelop["data"]["tot_size"])
                #print("fragment after merge = %d" % len(envelop["data"]["fragment"]))
                if envelop["data"]["tot_size"] == len(envelop["data"]["fragment"]):
                    parseNewsData(envelop["data"]["fragment"])
                else:
                    return None
        else:  # FRAG_NUM:1 The first fragment
            tot_size = int(fields_data["TOT_SIZE"])
            print("TOT_SIZE = %d" % tot_size)
            if tot_size == len(fragment):  # Completed News
                parseNewsData(fragment)
                pass
            else:
                #print("Receiving Multiple Fragments!!")
                print("Add new fragments to news envelop for guid %s" % guid)
                _news_envelopes.append({
                    "guid": guid,
                    "data": {
                        "fragment": fragment,
                        "mrn_src": mrn_src,
                        "frag_num": frag_num,
                        "tot_size": tot_size
                    }
                })
    except KeyError as keyerror:
        print('KeyError exception: ', keyerror)
    except zlib.error as error:
        print('zlib exception: ', error)
    except Exception as e:
        print('exception: ', sys.exc_info()[0])


def processStatus(ws, message_json):
    print("RECEIVED: Status Message")
    print(json.dumps(message_json, sort_keys=True, indent=2, separators=(',', ':')))


''' JSON-OMM Process functions '''


def process_message(ws, message_json):
    """ Parse at high level and output JSON of message """
    message_type = message_json['Type']
    message_domain = message_json['Domain']

    if message_type == "Refresh":
        if 'Domain' in message_json:
            #message_domain = message_json['Domain']
            if message_domain == "Login":
                process_login_response(ws, message_json)
            elif message_domain == mrn_domain:
                processRefresh(ws, message_json)
    elif message_type == "Update" and message_domain == mrn_domain:
        processUpdate(ws, message_json)
    elif message_type == "Status":
        processStatus(ws, message_json)
    elif message_type == "Ping":
        pong_json = {'Type': 'Pong'}
        ws.send(json.dumps(pong_json))
        print("SENT:")
        print(json.dumps(pong_json, sort_keys=True,
                         indent=2, separators=(',', ':')))


def process_login_response(ws, message_json):
    """ Send item request """
    # send_market_price_request(ws)
    send_mrn_request(ws)


def send_market_price_request(ws):
    """ Create and send simple Market Price request """
    mp_req_json = {
        'ID': 2,
        'Key': {
            'Name': ['EUR=', 'JPY=', 'THB='],
        },
    }
    ws.send(json.dumps(mp_req_json))
    print("SENT:")
    print(json.dumps(mp_req_json, sort_keys=True, indent=2, separators=(',', ':')))


def send_login_request(ws):
    """ Generate a login request from command line data (or defaults) and send """
    login_json = {
        'ID': 1,
        'Domain': 'Login',
        'Key': {
            'Name': '',
            'Elements': {
                'ApplicationId': '',
                'Position': ''
            }
        }
    }

    login_json['Key']['Name'] = user
    login_json['Key']['Elements']['ApplicationId'] = app_id
    login_json['Key']['Elements']['Position'] = position

    ws.send(json.dumps(login_json))
    print("SENT:")
    print(json.dumps(login_json, sort_keys=True, indent=2, separators=(',', ':')))


''' WebSocket Process functions '''


def on_message(ws, message):
    """ Called when message received, parse message into JSON for processing """
    #print("RECEIVED: ")
    message_json = json.loads(message)
    #print(json.dumps(message_json, sort_keys=True, indent=2, separators=(',', ':')))

    for singleMsg in message_json:
        process_message(ws, singleMsg)


def on_error(ws, error):
    """ Called when websocket error has occurred """
    print(error)


def on_close(ws):
    """ Called when websocket is closed """
    global web_socket_open
    print("WebSocket Closed")
    web_socket_open = False


def on_open(ws):
    """ Called when handshake is complete and websocket is open, send login """

    print("WebSocket successfully connected!")
    global web_socket_open
    web_socket_open = True
    send_login_request(ws)


''' Main Process Code '''

if __name__ == "__main__":

    # Get command line parameters
    try:
        opts, args = getopt.getopt(sys.argv[1:], "", [
                                   "help", "hostname=", "port=", "app_id=", "user=", "position="])
    except getopt.GetoptError:
        print(
            'Usage: market_price.py [--hostname hostname] [--port port] [--app_id app_id] [--user user] [--position position] [--help]')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("--help"):
            print(
                'Usage: market_price.py [--hostname hostname] [--port port] [--app_id app_id] [--user user] [--position position] [--help]')
            sys.exit(0)
        elif opt in ("--hostname"):
            hostname = arg
        elif opt in ("--port"):
            port = arg
        elif opt in ("--app_id"):
            app_id = arg
        elif opt in ("--user"):
            user = arg
        elif opt in ("--position"):
            position = arg

    # Start websocket handshake
    ws_address = "ws://{}:{}/WebSocket".format(hostname, port)
    print("Connecting to WebSocket " + ws_address + " ...")
    web_socket_app = websocket.WebSocketApp(ws_address, header=['User-Agent: Python'],
                                            on_message=on_message,
                                            on_error=on_error,
                                            on_close=on_close,
                                            subprotocols=['tr_json2'])
    web_socket_app.on_open = on_open

    # Event loop
    wst = threading.Thread(target=web_socket_app.run_forever)
    wst.start()

    try:
        while True:
            time.sleep(600)
    except KeyboardInterrupt:
        web_socket_app.close()
