# Elektron WebSocket API MRN Example with Python
- Last update: July 2019
- Environment: Windows and Linux OS 
- Compiler: Python
- Prerequisite: ADS and ADH servers version 3.2.1 and above, MRN service

## Overview

This example shows how to writing an application to subscribe Machine Readable News (MRN) using [Elektron WebSocket API](https://developers.refinitiv.com/elektron/websocket-api) from Thomson Reuters Enterprise Platform (TREP). The example just connects to TREP via a WebSocket connection, then subscribes and display MRN News data in a console. The project are implemented with Python language, but the main concept for consuming and assembling MRN News messages are the same for all technologies. 

*Note:* The news message is in UTF-8 JSON string format. Some news messages that contains special unicode character may not be able to show in Windows OS console (cmd, git bash, powershell, etc) due to the OS limitation. Those messages will be print as *UnicodeEncodeError exception. Cannot decode unicode character* message in a console instead.

## Machine Readable News Overview

Refinitiv Machine Readable News (MRN) is an advanced service for automating the consumption and systematic analysis of news. It delivers deep historical news archives, ultra-low latency structured news and news analytics directly to your applications. This enables algorithms to exploit the power of news to seize opportunities, capitalize on market inefficiencies and manage event risk.

### MRN Data model
MRN is published over Elektron using an Open Message Model (OMM) envelope in News Text Analytics domain messages. The Real-time News content set is made available over MRN_STORY RIC. The content data is contained in a FRAGMENT field that has been compressed, and potentially fragmented across multiple messages, in order to reduce bandwidth and message size.

A FRAGMENT field has a different data type based on a connection:
* RSSL connection: BUFFER type
* WebSocket connection: Base64 string

The data goes through the following series of transformations:

1. The core content data is a UTF-8 JSON string
2. This JSON string is compressed using gzip
3. The compressed JSON is split into a number of fragments (BUFFER or Base64 string) which each fit into a single update message
4. The data fragments are added to an update message as the FRAGMENT field value in a FieldList envelope

Therefore, in order to parse the core content data, the application will need to reverse this process. The WebSocket application also need to convert a received Base64 string in a FRAGMENT field to bytes data before further process this field.

If you are not familiar with MRN concept, please visit the following resources which will give you a full explanation of the MRN data behavior and how to process it:
* [Webinar Recording: Introduction to Machine Readable News](https://developers.refinitiv.com/news#news-accordion-nid-12045)
* [Introduction to Machine Readable News (MRN) with Elektron Message API (EMA)](https://developers.refinitiv.com/article/introduction-machine-readable-news-mrn-elektron-message-api-ema).
* [Machine Readable News (MRN) & N2_UBMS Comparison and Migration Guide](https://developers.refinitiv.com/article/machine-readable-news-mrn-n2_ubms-comparison-and-migration-guide).

## Prerequisite
This example requires the following dependencies softwares and libraries.
1. TREP server (both ADS and ADH) 3.2.x with WebSocket connection and MRN Service.
2. [Python](https://www.python.org/) compiler and runtime
3. Python's [requests 2.x](https://pypi.org/project/requests/) library.
4. Python's [websocket-client](https://pypi.org/project/websocket-client/) library (*version 0.49 or greater*).

*Note:* 
- The Python example has been qualified with Python versions 3.6.5. 
- Please refer to the [pip installation guide page](https://pip.pypa.io/en/stable/installing/) if your environment does not have the [pip tool](https://pypi.org/project/pip/) installed. 
- If your environment already have a websocket-client library installed, you can use ```pip list``` command to verify a library version, then use ```pip install --upgrade websocket-client``` command to upgrade websocket-client library. 
- It is not advisable to change the ADH/ADS configuration, if you are not familiar with the configuration procedures. Please consult your Market Data administrator for any questions regarding TREP-MRN service configuration.

## Application Files
This example project contains the following files and folders
1. *mrn_console_app.py*: The example application file
2. *requirements.txt*: The application dependencies configurationf file
3. LICENSE.md: Project's license file
4. README.md: Project's README file

## How to run this console example

Please be informed that your TREP server (ADS and ADH) should have a Service that contain MRN data.

1. Unzip or download the example project folder into a directory of your choice. 
2. Run ```$> pip install -r requestments.txt``` in a console to install all the dependencies libraries.
3. Then you can run mrn_console_app.py application with the following command
    ```
    $> python mrn_console_app.py --hostname <ADS server IP Address/Hostname> --port <WebSocket Port> --item <MRN RIC> --service <ADS Contribution Service name>
    ```

## References
* [Refinitiv Elektron SDK Family page](https://developers.refinitiv.com/elektron) on the [Refinitiv Developer Community](https://developers.thomsonreuters.com/) web site.
* [Refinitiv Elektron WebSocket API page](https://developers.refinitiv.com/websocket-api).
* [Developer Webinar Recording: Introduction to Electron WebSocket API](https://www.youtube.com/watch?v=CDKWMsIQfaw).
* [Machine Readable News (MRN) & N2_UBMS Comparison and Migration Guide](https://developers.refinitiv.com/article/machine-readable-news-mrn-n2_ubms-comparison-and-migration-guide).
* [Introduction to Machine Readable News (MRN) with Elektron Message API (EMA)](https://developers.refinitiv.com/article/introduction-machine-readable-news-mrn-elektron-message-api-ema).
* [Refinitiv-API-Samples/Example.WebSocketAPI.Javascript.NewsMonitor](https://github.com/Refinitiv-API-Samples/Example.WebSocketAPI.Javascript.NewsMonitor).

For any question related to this example or Elektron WebSocket API, please use the Developer Community [Q&A Forum](https://community.developers.refinitiv.com/spaces/152/websocket-api.html).