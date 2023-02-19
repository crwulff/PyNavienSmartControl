""" 
This module makes it possible to interact with Navien tankless water heater, 
combi-boiler or boiler connected via NaviLink.

Please refer to the documentation provided in the README.md,
which can be found at https://github.com/rudybrian/PyNavienSmartControl/

Note: "pip install requests" if getting import errors.
"""

__version__ = "1.0"
__author__ = "Brian Rudy"
__email__ = "brudy@praecogito.com"
__credits__ = ["matthew1471", "Gary T. Giesen"]
__date__ = "3/15/2022"
__license__ = "GPL"

import threading
import time
from concurrent.futures import Future
from datetime import date

# Third party library
import requests

# We unpack structures.
import struct

# We use namedtuple to reduce index errors.
import collections

# We use Python enums.
import enum

# We need json support for parsing the REST API response
import json

# UUID for a unique client ID
import uuid

# AWS MQTT
import awsiot.mqtt_connection_builder
import awscrt.auth
import awscrt.io
from awscrt.mqtt import QoS


class ControlType(enum.Enum):
    UNKNOWN = 0
    CHANNEL_INFORMATION = 1
    STATE = 2
    TREND_SAMPLE = 3
    TREND_MONTH = 4
    TREND_YEAR = 5
    ERROR_CODE = 6


class ChannelUse(enum.Enum):
    UNKNOWN = 0
    CHANNEL_1_USE = 1
    CHANNEL_2_USE = 2
    CHANNEL_1_2_USE = 3
    CHANNEL_3_USE = 4
    CHANNEL_1_3_USE = 5
    CHANNEL_2_3_USE = 6
    CHANNEL_1_2_3_USE = 7


class DeviceSorting(enum.Enum):
    NO_DEVICE = 0
    NPE = 1
    NCB = 2
    NHB = 3
    CAS_NPE = 4
    CAS_NHB = 5
    NFB = 6
    CAS_NFB = 7
    NFC = 8
    NPN = 9
    CAS_NPN = 10
    NPE2 = 11
    CAS_NPE2 = 12
    NCB_H = 13
    NVW = 14
    CAS_NVW = 15


class TemperatureType(enum.Enum):
    UNKNOWN = 0
    CELSIUS = 1
    FAHRENHEIT = 2


class OnDemandFlag(enum.Enum):
    UNKNOWN = 0
    ON = 1
    OFF = 2
    WARMUP = 3


class HeatingControl(enum.Enum):
    UNKNOWN = 0
    SUPPLY = 1
    RETURN = 2
    OUTSIDE_CONTROL = 3


class WWSDFlag(enum.Enum):
    OK = False
    FAIL = True


class WWSDMask(enum.Enum):
    WWSDFLAG = 0x01
    COMMERCIAL_LOCK = 0x02
    HOTWATER_POSSIBILITY = 0x04
    RECIRCULATION_POSSIBILITY = 0x08


class CommercialLockFlag(enum.Enum):
    OK = False
    LOCK = True


class NFBWaterFlag(enum.Enum):
    OFF = False
    ON = True


class RecirculationFlag(enum.Enum):
    OFF = False
    ON = True


class HighTemperature(enum.Enum):
    TEMPERATURE_60 = 0
    TEMPERATURE_83 = 1


class OnOFFFlag(enum.Enum):
    UNKNOWN = 0
    ON = 1
    OFF = 2


class DayOfWeek(enum.Enum):
    UN_KNOWN = 0
    SUN = 1
    MON = 2
    TUE = 3
    WED = 4
    THU = 5
    FRI = 6
    SAT = 7


class ControlSorting(enum.Enum):
    INFO = 1
    CONTROL = 2


class DeviceControl(enum.Enum):
    POWER = 1
    HEAT = 2
    WATER_TEMPERATURE = 3
    HEATING_WATER_TEMPERATURE = 4
    ON_DEMAND = 5
    WEEKLY = 6
    RECIRCULATION_TEMPERATURE = 7


"""
REST APIs:

https://nlus.naviensmartcontrol.com/api/v2/app/update-push-token
https://nlus.naviensmartcontrol.com/api/v2/app/version
https://nlus.naviensmartcontrol.com/api/v2/auth/email
https://nlus.naviensmartcontrol.com/api/v2/auth/email-confirm
https://nlus.naviensmartcontrol.com/api/v2/auth/refresh
https://nlus.naviensmartcontrol.com/api/v2/device/add
https://nlus.naviensmartcontrol.com/api/v2/device/change-info
https://nlus.naviensmartcontrol.com/api/v2/device/delete
https://nlus.naviensmartcontrol.com/api/v2/device/descaling/change-info
https://nlus.naviensmartcontrol.com/api/v2/device/error/list
https://nlus.naviensmartcontrol.com/api/v2/device/gas-type
https://nlus.naviensmartcontrol.com/api/v2/device/info
https://nlus.naviensmartcontrol.com/api/v2/device/list
https://nlus.naviensmartcontrol.com/api/v2/device/simple-list
https://nlus.naviensmartcontrol.com/api/v2/help/message/add
https://nlus.naviensmartcontrol.com/api/v2/help/message/delete
https://nlus.naviensmartcontrol.com/api/v2/help/message/info
https://nlus.naviensmartcontrol.com/api/v2/help/message/list
https://nlus.naviensmartcontrol.com/api/v2/help/message/owner-list
https://nlus.naviensmartcontrol.com/api/v2/help/message/reply
https://nlus.naviensmartcontrol.com/api/v2/user/add-installer
https://nlus.naviensmartcontrol.com/api/v2/user/add-member
https://nlus.naviensmartcontrol.com/api/v2/user/change-info/name
https://nlus.naviensmartcontrol.com/api/v2/user/change-info/phone-number
https://nlus.naviensmartcontrol.com/api/v2/user/change-password
https://nlus.naviensmartcontrol.com/api/v2/user/check-installer
https://nlus.naviensmartcontrol.com/api/v2/user/check-invite
https://nlus.naviensmartcontrol.com/api/v2/user/delegate
https://nlus.naviensmartcontrol.com/api/v2/user/delete-installer
https://nlus.naviensmartcontrol.com/api/v2/user/delete-member
https://nlus.naviensmartcontrol.com/api/v2/user/find-id
https://nlus.naviensmartcontrol.com/api/v2/user/get-agreement
https://nlus.naviensmartcontrol.com/api/v2/user/get-installer
https://nlus.naviensmartcontrol.com/api/v2/user/get-member
https://nlus.naviensmartcontrol.com/api/v2/user/get-owner
https://nlus.naviensmartcontrol.com/api/v2/user/get-push-settings
https://nlus.naviensmartcontrol.com/api/v2/user/info
https://nlus.naviensmartcontrol.com/api/v2/user/reset-password
https://nlus.naviensmartcontrol.com/api/v2/user/reset-password-legacy
https://nlus.naviensmartcontrol.com/api/v2/user/set-agreement
https://nlus.naviensmartcontrol.com/api/v2/user/set-push-settings
https://nlus.naviensmartcontrol.com/api/v2/user/sign-in
https://nlus.naviensmartcontrol.com/api/v2/user/sign-out
https://nlus.naviensmartcontrol.com/api/v2/user/sign-up
https://nlus.naviensmartcontrol.com/api/v2/user/withdrawal

MQTT APIs:

0x1000001: cmd/<device type>/navilink-<device mac>/status/start
0x1000002: cmd/<device type>/navilink-<device mac>/status/end
0x1000003: cmd/<device type>/navilink-<device mac>/status/channelinfo
0x1000004: cmd/<device type>/navilink-<device mac>/status/channelstatus
0x1000006: cmd/<device type>/navilink-<device mac>/status/weeklyschedule
0x1000007: cmd/<device type>/navilink-<device mac>/status/simpletrend
0x1000008: cmd/<device type>/navilink-<device mac>/status/hourlytrend
0x1000009: cmd/<device type>/navilink-<device mac>/status/dailytrend
0x100000A: cmd/<device type>/navilink-<device mac>/status/monthlytrend

cmd/<device type>/navilink-<device mac>/control
0x2000001: POWER
0x2000002: HEAT
0x2000003: WATER_TEMPERATURE
0x2000004: HEATING_WATER_TEMPERATURE
0x2000005: ON_DEMAND
0x2000006: WEEKLY
0x2000007: RECIRCULATION_TEMPERATURE
0x2000008: CIP_PERIOD
0x200000B: CIP_RESET
0x200000C: FILTER_RESET

"""


class NavienSmartControl:
    """
    The main NavienSmartControl class

    Example Usage:
        # Create an instance of this class
        navienSmartControl = NavienSmartControl('user@email.com', 'password')

        # Perform the REST login. Login information is returned, but required info is also saved inside this class.
        login = navienSmartControl.login()

        # Connect to the MQTT broker (uses information acquired from login)
        connectResult = navienSmartControl.connect()

        # Get the list of devices belonging to this user
        devlist = navienSmartControl.getDeviceList()

        # Pick a device to get information about
        dev = devlist[0]['deviceInfo']

        # Subscribe to messages from that device (most other MQTT APIs require this to work)
        navienSmartControl.subscribeDevice(dev)

        # Find the active channels on the device
        channelInfo = navienSmartControl.getChannelInfo(dev)

        # Pick a channel
        channel = channelInfo['channelList'][0]

        # Get information for the unit(s) on the selected channel
        channelStatus = navienSmartControl.getChannelStatus(dev, channel['channelNumber'])
    """

    # Enable debug messages
    enableDebug = False

    # Enable awscrt trace messages (very chatty)
    enableTrace = False

    # Headers for all requests. After login this will also contain the authorization header for follow-on requests
    requestHeaders = {"User-Agent": "okhttp/3.12.1", "Content-Type": "application/json"}

    # The Navien REST server.
    navienServer = "nlus.naviensmartcontrol.com"
    navienWebServer = "https://" + navienServer

    # The Navien MQTT server
    mqttServer = "a1t30mldyslmuq-ats.iot.us-east-1.amazonaws.com"

    def __init__(self, userID, passwd):
        """
        Construct a new 'NavienSmartControl' object.

        :param userID: The user ID used to log in to the mobile application
        :param passwd: The corresponding user's password
        :return: returns nothing
        """

        # REST Login credentials
        self.userID = userID
        self.passwd = passwd

        # MQTT login credentials
        self.accessKeyId = None
        self.secretKey = None
        self.sessionToken = None

        # MQTT client ID (supposed to be unique)
        self.uuid = str(uuid.uuid4())

        # MQTT connection and event loop
        self.connection = None
        self.event_loop_group = awscrt.io.EventLoopGroup(1)

        # Information useful for subscriptions
        self.userSeq = None

        # Futures used to wait for responses
        self.futures = {}

    #
    # REST APIs
    #

    def login(self):
        """
        Login to the REST API

        :return: The REST API response
        """
        response_data = self._request('user/sign-in', {"password": self.passwd, "userId": self.userID})

        if 'token' in response_data:
            token = response_data['token']
            if 'accessToken' in token:
                NavienSmartControl.requestHeaders.update({'authorization': token['accessToken']})
            if 'accessKeyId' in token:
                self.accessKeyId = token['accessKeyId']
            if 'secretKey' in token:
                self.secretKey = token['secretKey']
            if 'sessionToken' in token:
                self.sessionToken = token['sessionToken']

        if 'userInfo' in response_data:
            userInfo = response_data['userInfo']
            if 'userSeq' in userInfo:
                self.userSeq = userInfo['userSeq']

        return response_data

    def _request(self, api, data):
        response = requests.post(
            NavienSmartControl.navienWebServer + '/api/v2/' + api,
            headers=NavienSmartControl.requestHeaders,
            data=json.dumps(data),
        )

        if self.enableDebug:
            print(response.request.url)
            print(response.request.headers)
            print(response.request.body)

        return self._handleResponse(response)

    def _handleResponse(self, response):
        """
        HTTP response handler

        :param response: The response returned by the REST API request
        :return: The response JSON in dictionary form
        """
        # We need to check for the HTTP response code before attempting to parse the data
        if self.enableDebug:
            print(response.text)

        if response.status_code != 200:
            response_data = json.loads(response.text)
            if response_data["msg"] == "DB_ERROR":
                # Credentials invalid or some other error
                raise Exception(
                    "Error: "
                    + response_data["msg"]
                    + ": Login details incorrect. Please note, these are case-sensitive."
                )
            else:
                raise Exception("Error: " + response_data["msg"])

        response_data = json.loads(response.text)

        return response_data["data"]


    def getDeviceList(self):
        return self._request('device/list', {"count": 20, "offset": 0, "userId": self.userID})

    #
    # MQTT APIs
    #

    def connect(self):
        """
        Connect to the MQTT service

        :return: The response data (normally a channel information response)
        """

        if self.enableDebug:
            print("accessKeyId:" + self.accessKeyId)
            print("secretKey:" + self.secretKey)
            print("sessionToken:" + self.sessionToken)

        if self.enableTrace:
            awscrt.io.init_logging(awscrt.io.LogLevel.Trace, "stdout")

        credProvider = awscrt.auth.AwsCredentialsProvider.new_static(self.accessKeyId, self.secretKey, self.sessionToken)
        self.connection = awsiot.mqtt_connection_builder.websockets_with_default_aws_signing(
            'us-east-1', credProvider, endpoint=self.mqttServer, client_id=self.uuid)

        connectionFuture = self.connection.connect()
        connectionFuture.result()

        # DEBUG - Subscribe to everything and print out whatever we receive
        #def printmsg(topic, payload):
        #    print(topic, payload)
        #
        #subfuture, packetid = self.connection.subscribe("#", QoS.AT_LEAST_ONCE, printmsg)
        #print(subfuture.result())
        #
        # END DEBUG


    def subscribeDevice(self, dev):
        futures = []
        futures.extend(self._subscribe(dev, 'channelinfo', self._channelInfoCB))
        futures.extend(self._subscribe(dev, 'controlfail', self._controlFailCB))
        futures.extend(self._subscribe(dev, 'channelstatus', self._channelStatusCB))
        futures.extend(self._subscribe(dev, 'weeklyschedule', self._weeklyScheduleCB))
        futures.extend(self._subscribe(dev, 'simpletrend', self._simpleTrendCB))
        futures.extend(self._subscribe(dev, 'hourlytrend', self._hourlyTrendCB))
        futures.extend(self._subscribe(dev, 'dailytrend', self._dailyTrendCB))
        futures.extend(self._subscribe(dev, 'monthlytrend', self._monthlyTrendCB))
        f, p = self.connection.subscribe(self._cmdRequestTopic(dev, 'control', prefix=''), QoS.AT_LEAST_ONCE)
        futures.append(f)
        for f in futures:
            result = f.result()
            if self.enableDebug:
                print(result)

    def _cmdRequestTopic(self, dev, topic, prefix='status/'):
        return 'cmd/' + str(dev['deviceType']) + '/navilink-' + dev['macAddress'] + '/' + prefix + topic

    def _cmdResponseTopic(self, dev, topic):
        return 'cmd/' + str(dev['deviceType']) + '/' + str(dev['homeSeq']) + '/' + str(self.userSeq) + '/' + self.uuid + '/res/' + topic

    def _subscribe(self, dev, topic, callback):
        subfuture1, packetid = self.connection.subscribe(self._cmdRequestTopic(dev, topic), QoS.AT_LEAST_ONCE)
        subfuture2, packetid = self.connection.subscribe(self._cmdResponseTopic(dev, topic), QoS.AT_LEAST_ONCE, callback=callback)
        return [subfuture1, subfuture2]

    def _publish(self, topic, payload):
        self.connection.publish(topic, json.dumps(payload), QoS.AT_LEAST_ONCE)

    def _channelInfoCB(self, topic, payload):
        if self.enableDebug:
            print("CHANNEL INFO:", topic, payload)
        self.futures['channelInfo'].set_result(json.loads(payload)['response']['channelInfo'])

    def _controlFailCB(self, topic, payload):
        if self.enableDebug:
            print("CONTROL FAIL:", topic, payload)

    def _channelStatusCB(self, topic, payload):
        if self.enableDebug:
            print("CHANNEL STATUS:", topic, payload)
        self.futures['channelStatus'].set_result(json.loads(payload)['response']['channelStatus'])

    def _weeklyScheduleCB(self, topic, payload):
        if self.enableDebug:
            print("WEEKLY SCHEDULE:", topic, payload)

    def _simpleTrendCB(self, topic, payload):
        if self.enableDebug:
            print("SIMPLE TREND:", topic, payload)

    def _hourlyTrendCB(self, topic, payload):
        if self.enableDebug:
            print("HOURLY TREND:", topic, payload)

    def _dailyTrendCB(self, topic, payload):
        if self.enableDebug:
            print("DAILY TREND:", topic, payload)

    def _monthlyTrendCB(self, topic, payload):
        if self.enableDebug:
            print("MONTHLY TREND:", topic, payload)

    def getChannelInfo(self, dev) -> dict:
        """
        Get information about all active channels of the requested device.

        :param dev: Device to get channel info from
        :returns: {
            'channelCount': 1,
            'channelList': [{
                'channelNumber': 1,
                'channel': {
                    'unitType': 11,
                    'unitCount': 1,
                    'temperatureType': 2,
                    'setupDHWTempMin': 97,
                    'setupDHWTempMax': 185,
                    'setupHeatTempMin': 32,
                    'setupHeatTempMax': 32,
                    'onDemandUse': 2,
                    'heatControl': 1,
                    'wwsd': 2,
                    'commercialLock': 2,
                    'recirculationUse': 2,
                    'highTempDHWUse': 0,
                    'reCirculationSetupTempMin': 0,
                    'reCirculationSetupTempMax': 0,
                    'panelDipSwitchInfo': 0,
                    'mainDipSwitchInfo': 0,
                    'DHWTankSensorUse': 2,
                    'DHWUse': 2
                }
            }]
        }
        """

        requestTopic = self._cmdRequestTopic(dev, 'start')
        responseTopic = self._cmdResponseTopic(dev, 'channelinfo')

        self.futures['channelInfo'] = Future()
        self._publish(
            requestTopic,
            {'clientID': self.uuid,
             'protocolVersion': 1,
             'request': {'additionalValue': dev['additionalValue'],
                         'command': 0x1000001,
                         'deviceType': dev['deviceType'],
                         'macAddress': dev['macAddress']},
             'requestTopic': requestTopic,
             'responseTopic': responseTopic,
             'sessionID': str(int(time.time()*1000))})

        return self.futures['channelInfo'].result()

    def getChannelStatus(self, dev, channel, firstUnit=1, lastUnit=1) -> dict:
        """
        Get status from unit(s) on a channel of a device.

        :param dev: Device to get channel status from
        :param channel: Channel on Device to get channel status of
        :param firstUnit: First unit on the channel to get status for
        :param lastUnit: Last unit on the channel to get status for
        :return: {
            'channelNumber': 1,
            'channel': {
                'unitCount': 1,
                'unitType': 11,
                'operationUnitCount': 0,
                'weeklyControl': 2,
                'totalDayCount': 0,
                'avgCalorie': 0,
                'heatSettingTemp': 0,
                'powerStatus': 1,
                'heatStatus': 2,
                'onDemandUseFlag': 2,
                'avgOutletTemp': 103,
                'avgInletTemp': 105,
                'avgSupplyTemp': 32,
                'avgReturnTemp': 32,
                'recirculationSettingTemp': 0,
                'outdoorTemperature': 0,
                'unitInfo': {
                    'unitNumberStart': 1,
                    'unitNumberEnd': 1,
                    'unitStatusList': [{
                        'unitNumber': 1,
                        'controllerVersion': 3072,
                        'panelVersion': 4864,
                        'errorCode': 0,
                        'subErrorCode': 0,
                        'gasInstantUsage': 0,
                        'accumulatedGasUsage': 1147,
                        'currentOutletTemp': 103,    # Current outlet temperature (degrees F)
                        'currentInletTemp': 105,     # Current inlet temperature (degrees F)
                        'currentSupplyTemp': 32,
                        'currentReturnTemp': 32,
                        'currentRecirculationTemp': 0,
                        'currentOutputTDSValue': 0,
                        'accumulatedWaterUsage': 0,
                        'daysFilterUsed': 0,
                        'filterChange': 0,
                        'DHWFlowRate': 0,
                        'PoEStatus': 0,
                        'CIPSolutionRemained': 0,
                        'CIPStatus': 0,
                        'CIPOperationTimeHour': 0,
                        'CIPOperationTimeMin': 0,
                        'CIPSolutionSupplement': 0
                    }]
                },
                'DHWSettingTemp': 125
            }
        }
        """
        requestTopic = self._cmdRequestTopic(dev, 'channelstatus')
        responseTopic = self._cmdResponseTopic(dev, 'channelstatus')

        self.futures['channelStatus'] = Future()
        self._publish(
            requestTopic,
            {'clientID': self.uuid,
             'protocolVersion': 1,
             'request': {'additionalValue': dev['additionalValue'],
                         'command': 0x1000004,
                         'deviceType': dev['deviceType'],
                         'macAddress': dev['macAddress'],
                         'status': {'channelNumber': channel,
                                    'unitNumberStart': firstUnit,
                                    'unitNumberEnd': lastUnit}},
             'requestTopic': requestTopic,
             'responseTopic': responseTopic,
             'sessionID': str(int(time.time()*1000))})

        return self.futures['channelStatus'].result()

    def printChannelInformation(self, channelInformation):
        """
        Print Channel Information response data

        :param responseData: The parsed channel information response data
        """
        for chan in range(1, len(channelInformation["channel"]) + 1):
            print("Channel:" + str(chan))
            print(
                "\tDevice Model Type: "
                + DeviceSorting(
                    channelInformation["channel"][str(chan)]["deviceSorting"]
                ).name
            )
            print(
                "\tDevice Count: "
                + str(channelInformation["channel"][str(chan)]["deviceCount"])
            )
            print(
                "\tTemp Flag: "
                + TemperatureType(
                    channelInformation["channel"][str(chan)]["deviceTempFlag"]
                ).name
            )
            print(
                "\tMinimum Setting Water Temperature: "
                + str(
                    channelInformation["channel"][str(chan)][
                        "minimumSettingWaterTemperature"
                    ]
                )
            )
            print(
                "\tMaximum Setting Water Temperature: "
                + str(
                    channelInformation["channel"][str(chan)][
                        "maximumSettingWaterTemperature"
                    ]
                )
            )
            print(
                "\tHeating Minimum Setting Water Temperature: "
                + str(
                    channelInformation["channel"][str(chan)][
                        "heatingMinimumSettingWaterTemperature"
                    ]
                )
            )
            print(
                "\tHeating Maximum Setting Water Temperature: "
                + str(
                    channelInformation["channel"][str(chan)][
                        "heatingMaximumSettingWaterTemperature"
                    ]
                )
            )
            print(
                "\tUse On Demand: "
                + OnDemandFlag(
                    channelInformation["channel"][str(chan)]["useOnDemand"]
                ).name
            )
            print(
                "\tHeating Control: "
                + HeatingControl(
                    channelInformation["channel"][str(chan)]["heatingControl"]
                ).name
            )
            # Do some different stuff with the wwsdFlag value
            print(
                "\twwsdFlag: "
                + WWSDFlag(
                    (
                        channelInformation["channel"][str(chan)]["wwsdFlag"]
                        & WWSDMask.WWSDFLAG.value
                    )
                    > 0
                ).name
            )
            print(
                "\tcommercialLock: "
                + CommercialLockFlag(
                    (
                        channelInformation["channel"][str(chan)]["wwsdFlag"]
                        & WWSDMask.COMMERCIAL_LOCK.value
                    )
                    > 0
                ).name
            )
            print(
                "\thotwaterPossibility: "
                + NFBWaterFlag(
                    (
                        channelInformation["channel"][str(chan)]["wwsdFlag"]
                        & WWSDMask.HOTWATER_POSSIBILITY.value
                    )
                    > 0
                ).name
            )
            print(
                "\trecirculationPossibility: "
                + RecirculationFlag(
                    (
                        channelInformation["channel"][str(chan)]["wwsdFlag"]
                        & WWSDMask.RECIRCULATION_POSSIBILITY.value
                    )
                    > 0
                ).name
            )
            print(
                "\tHigh Temperature: "
                + HighTemperature(
                    channelInformation["channel"][str(chan)]["highTemperature"]
                ).name
            )
            print(
                "\tUse Warm Water: "
                + OnOFFFlag(
                    channelInformation["channel"][str(chan)]["useWarmWater"]
                ).name
            )
            # These values are ony populated with firmware version > 1500
            if (
                "minimumSettingRecirculationTemperature"
                in channelInformation["channel"][str(chan)]
            ):
                print(
                    "\tMinimum Recirculation Temperature: "
                    + channelInformation["channel"][str(chan)][
                        "minimumSettingRecirculationTemperature"
                    ]
                )
                print(
                    "\tMaximum Recirculation Temperature: "
                    + channelInformation["channel"][str(chan)][
                        "maximumSettingRecirculationTemperature"
                    ]
                )

    def printState(self, stateData, temperatureType):
        """
        Print State response data

        :param responseData: The parsed state response data
        :param temperatureType: The temperature type is used to determine if responses should be in metric or imperial units.
        """
        print(json.dumps(stateData, indent=2, default=str))
        print(
            "Controller Version: "
            + str(self.bigHexToInt(stateData["controllerVersion"]))
        )
        print("Panel Version: " + str(self.bigHexToInt(stateData["pannelVersion"])))
        print("Device Model Type: " + DeviceSorting(stateData["deviceSorting"]).name)
        print("Device Count: " + str(stateData["deviceCount"]))
        print("Current Channel: " + str(stateData["currentChannel"]))
        print("Device Number: " + str(stateData["deviceNumber"]))
        errorCD = self.bigHexToInt(stateData["errorCD"])
        if errorCD == 0:
            errorCD = "Normal"
        print("Error Code: " + str(errorCD))
        print("Operation Device Number: " + str(stateData["operationDeviceNumber"]))
        print(
            "Average Calorimeter: "
            + str(round(stateData["averageCalorimeter"] / 2.0, 1))
            + " %"
        )
        if temperatureType == TemperatureType.CELSIUS.value:
            if stateData["deviceSorting"] in [
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
            ]:
                GIUFactor = 100
            else:
                GIUFactor = 10
            # This needs to be summed for cascaded units
            print(
                "Current Gas Usage: "
                + str(
                    round(
                        (self.bigHexToInt(stateData["gasInstantUse"]) * GIUFactor)
                        / 10.0,
                        1,
                    )
                )
                + " kcal"
            )
            # This needs to be summed for cascaded units
            print(
                "Total Gas Usage: "
                + str(round(self.bigHexToInt(stateData["gasAccumulatedUse"]) / 10.0, 1))
                + " m"
                + u"\u00b3"
            )
            # only print these if DHW is in use
            if stateData["deviceSorting"] in [
                DeviceSorting.NPE.value,
                DeviceSorting.NPN.value,
                DeviceSorting.NPE2.value,
                DeviceSorting.NCB.value,
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
                DeviceSorting.CAS_NPE.value,
                DeviceSorting.CAS_NPN.value,
                DeviceSorting.CAS_NPE2.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
                DeviceSorting.CAS_NFB.value,
                DeviceSorting.CAS_NVW.value,
            ]:
                print(
                    "Hot Water Setting Temperature: "
                    + str(round(stateData["hotWaterSettingTemperature"] / 2.0, 1))
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                if str(DeviceSorting(stateData["deviceSorting"]).name).startswith(
                    "CAS_"
                ):
                    print(
                        "Hot Water Average Temperature: "
                        + str(round(stateData["hotWaterAverageTemperature"] / 2.0, 1))
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                    print(
                        "Inlet Average Temperature: "
                        + str(round(stateData["inletAverageTemperature"] / 2.0, 1))
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                print(
                    "Hot Water Current Temperature: "
                    + str(round(stateData["hotWaterCurrentTemperature"] / 2.0, 1))
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                print(
                    "Hot Water Flow Rate: "
                    + str(
                        round(self.bigHexToInt(stateData["hotWaterFlowRate"]) / 10.0, 1)
                    )
                    + " LPM"
                )
                print(
                    "Inlet Temperature: "
                    + str(round(stateData["hotWaterTemperature"] / 2.0, 1))
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                if "recirculationSettingTemperature" in stateData:
                    print(
                        "Recirculation Setting Temperature: "
                        + str(
                            round(stateData["recirculationSettingTemperature"] / 2.0, 1)
                        )
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                    print(
                        "Recirculation Current Temperature: "
                        + str(
                            round(stateData["recirculationCurrentTemperature"] / 2.0, 1)
                        )
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
            # Only print these if CH is in use
            if stateData["deviceSorting"] in [
                DeviceSorting.NHB.value,
                DeviceSorting.CAS_NHB.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
                DeviceSorting.CAS_NFB.value,
                DeviceSorting.CAS_NVW.value,
                DeviceSorting.NCB.value,
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
            ]:
                # Don't show the setting for cascaded devices, as it isn't applicable
                print(
                    "Heat Setting Temperature: "
                    + str(round(stateData["heatSettingTemperature"] / 2.0, 1))
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                if str(DeviceSorting(stateData["deviceSorting"]).name).startswith(
                    "CAS_"
                ):
                    print(
                        "Supply Average Temperature: "
                        + str(round(stateData["supplyAverageTemperature"] / 2.0, 1))
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                    print(
                        "Return Average Temperature: "
                        + str(round(stateData["returnAverageTemperature"] / 2.0, 1))
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                print(
                    "Current Supply Water Temperature: "
                    + str(round(stateData["currentWorkingFluidTemperature"] / 2.0, 1))
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                print(
                    "Current Return Water Temperature: "
                    + str(round(stateData["currentReturnWaterTemperature"] / 2.0), 1)
                    + " "
                    + u"\u00b0"
                    + "C"
                )
        elif temperatureType == TemperatureType.FAHRENHEIT.value:
            if stateData["deviceSorting"] in [
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
            ]:
                GIUFactor = 10
            else:
                GIUFactor = 1
            # This needs to be summed for cascaded units
            print(
                "Current Gas Usage: "
                + str(
                    round(
                        self.bigHexToInt(stateData["gasInstantUse"])
                        * GIUFactor
                        * 3.968,
                        1,
                    )
                )
                + " BTU"
            )
            # This needs to be summed for cascaded units
            print(
                "Total Gas Usage: "
                + str(
                    round(
                        (self.bigHexToInt(stateData["gasAccumulatedUse"]) * 35.314667)
                        / 10.0,
                        1,
                    )
                )
                + " ft"
                + u"\u00b3"
            )
            # only print these if DHW is in use
            if stateData["deviceSorting"] in [
                DeviceSorting.NPE.value,
                DeviceSorting.NPN.value,
                DeviceSorting.NPE2.value,
                DeviceSorting.NCB.value,
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
                DeviceSorting.CAS_NPE.value,
                DeviceSorting.CAS_NPN.value,
                DeviceSorting.CAS_NPE2.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
                DeviceSorting.CAS_NFB.value,
                DeviceSorting.CAS_NVW.value,
            ]:
                print(
                    "Hot Water Setting Temperature: "
                    + str(stateData["hotWaterSettingTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                if str(DeviceSorting(stateData["deviceSorting"]).name).startswith(
                    "CAS_"
                ):
                    print(
                        "Hot Water Average Temperature: "
                        + str(stateData["hotWaterAverageTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
                    print(
                        "Inlet Average Temperature: "
                        + str(stateData["inletAverageTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
                print(
                    "Hot Water Current Temperature: "
                    + str(stateData["hotWaterCurrentTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                print(
                    "Hot Water Flow Rate: "
                    + str(
                        round(
                            (self.bigHexToInt(stateData["hotWaterFlowRate"]) / 3.785)
                            / 10.0,
                            1,
                        )
                    )
                    + " GPM"
                )
                print(
                    "Inlet Temperature: "
                    + str(stateData["hotWaterTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                if "recirculationSettingTemperature" in stateData:
                    print(
                        "Recirculation Setting Temperature: "
                        + str(stateData["recirculationSettingTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
                    print(
                        "Recirculation Current Temperature: "
                        + str(stateData["recirculationCurrentTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
            # Only print these if CH is in use
            if stateData["deviceSorting"] in [
                DeviceSorting.NHB.value,
                DeviceSorting.CAS_NHB.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
                DeviceSorting.CAS_NFB.value,
                DeviceSorting.CAS_NVW.value,
                DeviceSorting.NCB.value,
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
            ]:
                # Don't show the setting for cascaded devices, as it isn't applicable
                print(
                    "Heat Setting Temperature: "
                    + str(stateData["heatSettingTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                if str(DeviceSorting(stateData["deviceSorting"]).name).startswith(
                    "CAS_"
                ):
                    print(
                        "Supply Average Temperature: "
                        + str(stateData["supplyAverageTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
                    print(
                        "Return Average Temperature: "
                        + str(stateData["returnAverageTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
                print(
                    "Current Supply Water Temperature: "
                    + str(stateData["currentWorkingFluidTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                print(
                    "Current Return Water Temperature: "
                    + str(stateData["currentReturnWaterTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
        else:
            raise Exception("Error: Invalid temperatureType")

        print("Power Status: " + OnOFFFlag(stateData["powerStatus"]).name)
        print("Heat Status: " + OnOFFFlag(stateData["heatStatus"]).name)
        print("Use On Demand: " + OnDemandFlag(stateData["useOnDemand"]).name)
        print("Weekly Control: " + OnOFFFlag(stateData["weeklyControl"]).name)
        # Print the daySequences
        print("Day Sequences")
        for i in range(7):
            print("\t" + DayOfWeek(stateData["daySequences"][i]["dayOfWeek"]).name)
            if "daySequence" in stateData["daySequences"][i]:
                for j in stateData["daySequences"][i]["daySequence"]:
                    print(
                        "\t\tHour: "
                        + str(stateData["daySequences"][i]["daySequence"][j]["hour"])
                        + ", Minute: "
                        + str(stateData["daySequences"][i]["daySequence"][j]["minute"])
                        + ", "
                        + OnOFFFlag(
                            stateData["daySequences"][i]["daySequence"][j]["isOnOFF"]
                        ).name
                    )
            else:
                print("\t\tNone")

    def printTrendSample(self, trendSampleData, temperatureType):
        """
        Print the trend sample response data
        
        :param responseData: The parsed trend sample response data
        :param temperatureType: The temperature type is used to determine if responses should be in metric or imperial units.
        """
        # print(json.dumps(trendSampleData, indent=2, default=str))
        print(
            "Controller Version: "
            + str(self.bigHexToInt(trendSampleData["controllerVersion"]))
        )
        print(
            "Panel Version: " + str(self.bigHexToInt(trendSampleData["pannelVersion"]))
        )
        print(
            "Device Model Type: " + DeviceSorting(trendSampleData["deviceSorting"]).name
        )
        print("Device Count: " + str(trendSampleData["deviceCount"]))
        print("Current Channel: " + str(trendSampleData["currentChannel"]))
        print("Device Number: " + str(trendSampleData["deviceNumber"]))
        print("Model Info: " + str(self.bigHexToInt(trendSampleData["modelInfo"])))
        print(
            "Total Operated Time: "
            + str(self.bigHexToInt(trendSampleData["totalOperatedTime"]))
        )
        # totalGasAccumulateSum needs to be converted based on the metric or imperial setting
        if temperatureType == TemperatureType.CELSIUS.value:
            print(
                "Total Gas Accumulated Sum: "
                + str(
                    round(
                        self.bigHexToInt(trendSampleData["totalGasAccumulateSum"])
                        / 10.0,
                        1,
                    )
                )
                + " m"
                + u"\u00b3"
            )
        else:
            print(
                "Total Gas Accumulated Sum: "
                + str(
                    round(
                        (
                            self.bigHexToInt(trendSampleData["totalGasAccumulateSum"])
                            * 35.314667
                        )
                        / 10.0,
                        1,
                    )
                )
                + " ft"
                + u"\u00b3"
            )
        print(
            "Total Hot Water Accumulated Sum: "
            + str(self.bigHexToInt(trendSampleData["totalHotWaterAccumulateSum"]))
        )
        print(
            "Total Central Heating Operated Time: "
            + str(self.bigHexToInt(trendSampleData["totalCHOperatedTime"]))
        )
        if "totalDHWUsageTime" in trendSampleData:
            print(
                "Total Domestic Hot Water Usage Time: "
                + str(self.bigHexToInt(trendSampleData["totalDHWUsageTime"]))
            )

    def printTrendMY(self, trendMYData, temperatureType):
        """
        Print the trend month or year response data
        
        :param responseData: The parsed trend month or year response data
        :param temperatureType: The temperature type is used to determine if responses should be in metric or imperial units.
        """
        # print(json.dumps(trendMYData, indent=2, default=str))
        print(
            "Controller Version: "
            + str(self.bigHexToInt(trendMYData["controllerVersion"]))
        )
        print("Panel Version: " + str(self.bigHexToInt(trendMYData["pannelVersion"])))
        print("Device Model Type: " + DeviceSorting(trendMYData["deviceSorting"]).name)
        print("Device Count: " + str(trendMYData["deviceCount"]))
        print("Current Channel: " + str(trendMYData["currentChannel"]))
        print("Device Number: " + str(trendMYData["deviceNumber"]))
        # Print the trend data
        for i in range(trendMYData["totalDaySequence"]):
            print(
                "\tIndex: "
                + str(self.bigHexToInt(trendMYData["trendSequences"][i]["dMIndex"]))
            )
            print(
                "\t\tModel Info: "
                + str(
                    self.bigHexToInt(
                        trendMYData["trendSequences"][i]["trendData"]["modelInfo"]
                    )
                )
            )
            print(
                "\t\tHot Water Operated Count: "
                + str(
                    self.bigHexToInt(
                        trendMYData["trendSequences"][i]["trendData"][
                            "hotWaterOperatedCount"
                        ]
                    )
                )
            )
            print(
                "\t\tOn Demand Use Count: "
                + str(
                    self.bigHexToInt(
                        trendMYData["trendSequences"][i]["trendData"][
                            "onDemandUseCount"
                        ]
                    )
                )
            )
            print(
                "\t\tHeat Accumulated Use: "
                + str(
                    self.bigHexToInt(
                        trendMYData["trendSequences"][i]["trendData"][
                            "heatAccumulatedUse"
                        ]
                    )
                )
            )
            print(
                "\t\tDomestic Hot Water Accumulated Use: "
                + str(
                    self.bigHexToInt(
                        trendMYData["trendSequences"][i]["trendData"][
                            "dHWAccumulatedUse"
                        ]
                    )
                )
            )
            if temperatureType == TemperatureType.CELSIUS.value:
                print(
                    "\t\tTotal Gas Usage: "
                    + str(
                        round(
                            self.bigHexToInt(
                                trendMYData["trendSequences"][i]["trendData"][
                                    "gasAccumulatedUse"
                                ]
                            )
                            / 10.0,
                            1,
                        )
                    )
                    + " m"
                    + u"\u00b3"
                )
                print(
                    "\t\tHot water Accumulated Use: "
                    + str(
                        round(
                            self.bigHexToInt(
                                trendMYData["trendSequences"][i]["trendData"][
                                    "hotWaterAccumulatedUse"
                                ]
                            )
                            / 10.0,
                            1,
                        )
                    )
                    + " L"
                )
                print(
                    "\t\tOutdoor Air Max Temperature: "
                    + str(
                        round(
                            trendMYData["trendSequences"][i]["trendData"][
                                "outdoorAirMaxTemperature"
                            ]
                            / 2.0,
                            1,
                        )
                    )
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                print(
                    "\t\tOutdoor Air Min Temperature: "
                    + str(
                        round(
                            trendMYData["trendSequences"][i]["trendData"][
                                "outdoorAirMinTemperature"
                            ]
                            / 2.0,
                            1,
                        )
                    )
                    + " "
                    + u"\u00b0"
                    + "C"
                )
            elif temperatureType == TemperatureType.FAHRENHEIT.value:
                print(
                    "\t\tTotal Gas Usage: "
                    + str(
                        round(
                            (
                                self.bigHexToInt(
                                    trendMYData["trendSequences"][i]["trendData"][
                                        "gasAccumulatedUse"
                                    ]
                                )
                                * 35.314667
                            )
                            / 10.0,
                            1,
                        )
                    )
                    + " ft"
                    + u"\u00b3"
                )
                print(
                    "\t\tHot water Accumulated Use: "
                    + str(
                        round(
                            (
                                self.bigHexToInt(
                                    trendMYData["trendSequences"][i]["trendData"][
                                        "hotWaterAccumulatedUse"
                                    ]
                                )
                                / 3.785
                            )
                            / 10.0,
                            1,
                        )
                    )
                    + " G"
                )
                print(
                    "\t\tOutdoor Air Max Temperature: "
                    + str(
                        trendMYData["trendSequences"][i]["trendData"][
                            "outdoorAirMaxTemperature"
                        ]
                    )
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                print(
                    "\t\tOutdoor Air Min Temperature: "
                    + str(
                        trendMYData["trendSequences"][i]["trendData"][
                            "outdoorAirMinTemperature"
                        ]
                    )
                    + " "
                    + u"\u00b0"
                    + "F"
                )
            else:
                raise Exception("Error: Invalid temperatureType")

    def printError(self, errorData, temperatureType):
        """
        Print an error response
        
        :param responseData: The parsed error presponse data
        :param temperatureType: The temperature type is used to determine if responses should be in metric or imperial units.
        """
        print(
            "Controller Version: "
            + str(self.bigHexToInt(errorData["controllerVersion"]))
        )
        print("Panel Version: " + str(self.bigHexToInt(errorData["pannelVersion"])))
        print("Device Model Type: " + DeviceSorting(errorData["deviceSorting"]).name)
        print("Device Count: " + str(errorData["deviceCount"]))
        print("Current Channel: " + str(errorData["currentChannel"]))
        print("Device Number: " + str(errorData["deviceNumber"]))
        # not sure how to parse these, so just print them as numbers
        print("Error Flag: " + str(errorData["errorFlag"]))
        print("Error Code: " + str(self.bigHexToInt(errorData["errorCD"])))

    def bigHexToInt(self, hex):
        """
        Convert from a list of big endian hex byte array or string to an integer
        
        :param hex: Big-endian string, int or byte array to be converted
        :return: Integer after little-endian conversion
        """
        if isinstance(hex, str):
            hex = bytearray(hex)
        if isinstance(hex, int):
            # This is already an int, just return it
            return hex
        bigEndianStr = "".join("%02x" % b for b in hex)
        littleHex = bytearray.fromhex(bigEndianStr)
        littleHex.reverse()
        littleHexStr = "".join("%02x" % b for b in littleHex)
        return int(littleHexStr, 16)

