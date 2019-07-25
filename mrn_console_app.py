# |-----------------------------------------------------------------------------
# |            This source code is provided under the Apache 2.0 license      --
# |  and is provided AS IS with no warranty or guarantee of fit for purpose.  --
# |                See the project's LICENSE.md for details.                  --
# |           Copyright Refinitiv 2019. All rights reserved.            --
# |-----------------------------------------------------------------------------


#!/usr/bin/env python
""" Simple example of outputting Machine Readable News JSON data using Websockets """

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
hostname = '127.0.0.1'
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
        "Domain": mrn_domain,
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


def processMRNUpdate(ws, message_json):  # process incoming News Update messages

    fields_data = message_json["Fields"]
    # Dump the FieldList first (for informational purposes)
    # decodeFieldList(message_json["Fields"])

    # declare variables
    tot_size = 0
    guid = None

    try:
        # Get data for all requried fields
        fragment = base64.b64decode(fields_data["FRAGMENT"])
        frag_num = int(fields_data["FRAG_NUM"])
        guid = fields_data["GUID"]
        mrn_src = fields_data["MRN_SRC"]

        #print("GUID  = %s" % guid)
        #print("FRAG_NUM = %d" % frag_num)
        #print("MRN_SRC = %s" % mrn_src)

        if frag_num > 1:  # We are now processing more than one part of an envelope - retrieve the current details
            guid_index = next((index for (index, d) in enumerate(
                _news_envelopes) if d["guid"] == guid), None)
            envelop = _news_envelopes[guid_index]
            if envelop and envelop["data"]["mrn_src"] == mrn_src and frag_num == envelop["data"]["frag_num"] + 1:
                print("process multiple fragments for guid %s" %
                      envelop["guid"])

                #print("fragment before merge = %d" % len(envelop["data"]["fragment"]))

                # Merge incoming data to existing news envelop and getting FRAGMENT and TOT_SIZE data to local variables
                fragment = envelop["data"]["fragment"] = envelop["data"]["fragment"] + fragment
                envelop["data"]["frag_num"] = frag_num
                tot_size = envelop["data"]["tot_size"]
                print("TOT_SIZE = %d" % tot_size)
                print("Current FRAGMENT length = %d" % len(fragment))

                # The multiple fragments news are not completed, waiting.
                if tot_size != len(fragment):
                    return None
                # The multiple fragments news are completed, delete assoiclate GUID envelop
                elif tot_size == len(fragment):
                    del _news_envelopes[guid_index]
            else:
                print("Error: Cannot find fragment for GUID %s with matching FRAG_NUM or MRN_SRC %s" % (
                    guid, mrn_src))
                return None
        else:  # FRAG_NUM = 1 The first fragment
            tot_size = int(fields_data["TOT_SIZE"])
            print("FRAGMENT length = %d" % len(fragment))
            # The fragment news is not completed, waiting and add this news data to envelop object.
            if tot_size != len(fragment):
                print("Add new fragments to news envelop for guid %s" % guid)
                _news_envelopes.append({  # the envelop object is a Python dictionary with GUID as a key and other fields are data
                    "guid": guid,
                    "data": {
                        "fragment": fragment,
                        "mrn_src": mrn_src,
                        "frag_num": frag_num,
                        "tot_size": tot_size
                    }
                })
                return None

        # News Fragment(s) completed, decompress and print data as JSON to console
        if tot_size == len(fragment):
            print("decompress News FRAGMENT(s) for GUID  %s" % guid)
            decompressed_data = zlib.decompress(fragment, zlib.MAX_WBITS | 32)
            print("News = %s" % json.loads(decompressed_data))

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
        print("UnicodeEncodeError exception. Cannot decode unicode character for %s in this enviroment: " %
              guid, encodeerror)
    except Exception as e:
        print('exception: ', sys.exc_info()[0])


def processStatus(ws, message_json):  # process incoming status message
    print("RECEIVED: Status Message")
    print(json.dumps(message_json, sort_keys=True, indent=2, separators=(',', ':')))


''' JSON-OMM Process functions '''


def process_message(ws, message_json):
    """ Parse at high level and output JSON of message """
    message_type = message_json['Type']

    if message_type == "Refresh":
        if "Domain" in message_json:
            message_domain = message_json["Domain"]
            if message_domain == "Login":
                process_login_response(ws, message_json)
            elif message_domain:
                processRefresh(ws, message_json)
    elif message_type == "Update":
        if "Domain" in message_json and message_json["Domain"] == mrn_domain:
            processMRNUpdate(ws, message_json)
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
    send_mrn_request(ws)


def send_login_request(ws):
    """ Generate a login request from command line data (or defaults) and send """
    login_json = {
        'ID': 1,
        "Domain": 'Login',
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
    print("RECEIVED: ")
    message_json = json.loads(message)
    print(json.dumps(message_json, sort_keys=True, indent=2, separators=(',', ':')))

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
                                   "help", "hostname=", "port=", "app_id=", "user=", "position=", "ric="])
    except getopt.GetoptError:
        print(
            'Usage: market_price.py [--hostname hostname] [--port port] [--app_id app_id] [--user user] [--position position] [--ric news RIC name] [--help]')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("--help"):
            print(
                'Usage: market_price.py [--hostname hostname] [--port port] [--app_id app_id] [--user user] [--position position] [--ric news RIC name] [--help]')
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
        elif opt in ("--ric"):
            if arg not in ["MRN_STORY", "MRN_TRNA", "MRN_TRNA_DOC", "MRN_TRSI"]:
                print(
                    "The supported MRN RIC names are MRN_STORY or MRN_TRNA or MRN_TRNA_DOC or MRN_TRSI only")
                sys.exit(2)
            else:
                item = arg

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
            time.sleep(1)
    except KeyboardInterrupt:
        web_socket_app.close()
