# iRobot plugin based on rest980 api
# Author: ajarzyna, 2020
"""
<plugin key="REST980" name="iRobot based on rest980" author="ajarzyn" version="0.0.2">
    <description>
        <h2>iRobot based on rest980</h2><br/>
        This plugins uses rest980 by koalazak, to control iRobot.

        Be aware:
         Values greater than 30 seconds will cause a message to be regularly logged about the plugin not responding.
         The plugin will actually function correctly with values greater than 30 though.
    </description>
    <params>
        <param field="Address" label="rest980's IP Address" width="200px" required="true" default="127.0.0.1"/>
        <param field="Port" label="rest980's Port" width="30px" required="true" default="3000"/>
        <param field="Mode1" label="Display battery status in name" width="150px">
            <options>
                <option label="Yes" value="1"/>
                <option label="No" value="0" default="true"/>
            </options>
        </param>
        <param field="Mode2" label="Data pull interval in seconds" width="150px" default="25"/>
        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0" default="true"/>
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Python" value="18"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
            </options>
        </param>
    </params>

</plugin>
"""

import Domoticz
import json
import queue


class Rest980Api:
    def __init__(self):
        self.base_local_url = "/api/local"
        self.base_cloud_url = "/api/cloud"
        self.action = "/action"
        self.info = "/info"

        self.actions = {00: "/stop",
                        10: "/start",
                        20: "/pause",
                        30: "/resume",
                        40: "/dock",
                        50: "/cleanRoom"}

        self.infos = ["mission",
                      "wireless",
                      "lastwireless",
                      "sys",
                      "sku",
                      "state"]

    def get_local_url(self, command):
        if command in self.actions.keys():
            return self.base_local_url + self.action + self.actions[command]
        elif command in self.actions.values():
            return self.base_local_url + self.action + command
        elif command in self.infos:
            return self.base_local_url + self.info + "/" + command

    def translate_command_to_val(self, command):
        for act in self.actions:
            if command in self.actions[act]:
                return act
        return -1

    def is_action(self, item):
        return item in self.actions


# add icons for roomba, maybe from: https://thenounproject.com/term/roomba/3177860/
class BasePlugin:
    def __init__(self):
        self.http_conn = None
        self.runAgain = 6
        self.disconnectCount = 0
        self.sProtocol = "HTTP"

        self.bat_level = 100
        self.AVAILABLE_LEVELS = [00, 10, 20, 30, 40]

        self._wait_for_update = True
        self.repeat_request = 5

        self.UNITS = {
            'Working': [1, dict(TypeName="Switch", Image=9, Used=1)],
            'Advanced': [2, dict(TypeName="Selector Switch", Used=9, Image=7,
                                 Options={"LevelActions": "|||||",
                                          "LevelNames": "stop|start|pause|resume|dock|cleanRoom",
                                          "LevelOffHidden": "false",
                                          "SelectorStyle": "1"})],
            # 'Phase': 3,
            'Bin': [4, dict(TypeName="Alert", Image=9, Used=1)],
        }

        for unit in self.UNITS:
            self.UNITS[unit][1].update(dict(Name=unit, Unit=self.UNITS[unit][0]))

        self.rest_api = Rest980Api()
        self.que = queue.Queue()
        return

    def CreateDevices(self):
        for unit in self.UNITS:
            if self._get_dev_id(unit) not in Devices:
                Domoticz.Device(**self.UNITS[unit][1]).Create()

    def InitializeREST980Connection(self):
        self.http_conn = Domoticz.Connection(Name=self.sProtocol + " MAIN",
                                             Transport="TCP/IP",
                                             Protocol=self.sProtocol,
                                             Address=self.host,
                                             Port=self.port)
        self.http_conn.Connect()

    def onStart(self):
        self.name = Parameters['Name']
        self.host = Parameters['Address']
        self.port = Parameters['Port']

        Domoticz.Heartbeat(int(Parameters['Mode2']))

        self.display_battery_in_name = Parameters['Mode1']

        self.headers = {'Content-Type': 'text/xml; charset=utf-8',
                        'Connection': 'keep-alive',
                        'Accept': 'Content-Type: text/html; charset=UTF-8',
                        'Host': self.host + ":" + self.port,
                        'User-Agent': 'Domoticz/1.0'}

        self.send_data = {'Verb': 'GET',
                          'URL': '/',
                          'Headers': self.headers}

        if Parameters["Mode6"] != "0":
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()

        # Create connection to rest980
        self.InitializeREST980Connection()

        # Create devices for roomba
        self.CreateDevices()
        self._request_devices_state()


    def onStop(self):
        Domoticz.Debug("onStop - Plugin is stopping.")
        _l_con = self.http_conn
        if self.isConnected(_l_con, False):
            _l_con.Disconnect()
        self.http_conn = None

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called for connection to: "+Connection.Address+":"+Connection.Port)

    def onConnect(self, Connection, status, Description):
        if status == 0:
            Domoticz.Debug("rest980 connected successfully.")
            while not self.que.empty():
                item = self.que.get()
                if self.rest_api.is_action(item):
                    data_refresh = True
                else:
                    data_refresh = False
                self._sent_message(Connection, item, data_refresh)
        else:
            Domoticz.Log("Failed to connect (" + str(status)
                         + ") to: " + self.host + ":" + self.port
                         + " with error: " + Description)

    def onMessage(self, Connection, Data):
        status = int(Data["Status"])
        Domoticz.Debug("Status: " + str(status))
        if status == 200:
            str_data = json.loads(Data["Data"].decode("utf-8", "ignore"))
            Domoticz.Debug("json: " + str(str_data.keys()))
            if 'ok' in str_data.keys():
                Domoticz.Debug(str(str_data.values()))
                if str_data['ok'] is None:
                    self._request_devices_state(Connection)
                return
            if "batPct" in str_data.keys():
                do_update_name_or_time = False
                if str(str_data['name']) != self.name:
                    self.name = str(str_data['name'])
                    do_update_name_or_time = True
                if self.bat_level != str_data['batPct']:
                    self.bat_level = str_data['batPct']
                    do_update_name_or_time = True

                to_update = {}
                if do_update_name_or_time:
                    for unit in self.UNITS:
                        name = self.name + " " + unit
                        if self.display_battery_in_name != "0":
                            name += " " + str(self.bat_level) + "%"
                        to_update[unit] = dict(unit=self._get_dev_id(unit),
                                               name=name,
                                               bat_lvl=self.bat_level)

                key = "Working"
                if "run" == str_data['cleanMissionStatus']['phase'] and self._get_dev(key).nValue == 0:
                    update_dict(to_update, key, dict(unit=self._get_dev_id(key), n_value=1, s_value="On"))
                elif "run" != str_data['cleanMissionStatus']['phase'] and self._get_dev(key).nValue == 1:
                    update_dict(to_update, key, dict(unit=self._get_dev_id(key), n_value=0, s_value="Off"))

                key = "Advanced"
                last_level = self.rest_api.translate_command_to_val(str_data['lastCommand']['command'])
                Domoticz.Debug("Advanced: " + str(last_level) + " prev " + str(self._get_dev(key).nValue))
                if last_level != -1 and last_level != self._get_dev(key).nValue:
                    update_dict(to_update, key, dict(unit=self._get_dev_id(key), n_value=last_level, s_value=last_level))

                key = "Bin"
                if str_data['bin']['full']:
                    n_val = 1
                    s_val = "On"
                else:
                    n_val = 0
                    s_val = "Off"
                if n_val != self._get_dev(key).nValue:
                    update_dict(to_update, key, dict(unit=self._get_dev_id(key), n_value=n_val, s_value=s_val))

                if self._wait_for_update and not to_update and self.repeat_request:
                    self.repeat_request -= 1
                    self._request_devices_state(Connection)
                    return
                else:
                    self.repeat_request = 5
                    self._wait_for_update = False

                for dev_dict in to_update:
                    Domoticz.Debug(str(dev_dict))
                    Domoticz.Debug(str(to_update[dev_dict]))
                    update_device(**to_update[dev_dict])

        elif status == 302:
            Domoticz.Log("Page Moved Error.")
            send_data['URL'] = Data["Headers"]["Location"]
            Domoticz.Debug(type(send_data))
            Connection.Send(send_data)
        elif status == 400:
            Domoticz.Error("rest980 returned a Bad Request Error.")
        elif status == 500:
            Domoticz.Error("rest980 returned a Server Error.")
        else:
            Domoticz.Error("rest980 returned a status: "+str(status))

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

        if self._wait_for_update:
            Domoticz.Debug('Waiting for device update. State changes not possible.')
            return

        while not self.que.empty():
            self.que.get()

        if Unit == self._get_dev_id('Advanced'):
            if Level in self.AVAILABLE_LEVELS:
                self._sent_message(self.http_conn, Level, request_device_state_update=True)
            else:
                Domoticz.Log("This mode is not supported yet.")
            return

        if Unit == self._get_dev_id('Working'):
            if Command == 'Off':
                roomba_command = "/pause"
            elif Command == 'On':
                if self._get_dev('Advanced').nValue == 20:
                    roomba_command = "/resume"
                else:
                    roomba_command = "/start"
            else:
                Domoticz.Error("Unknown command for 'Working' device.")
                return

            self._sent_message(self.http_conn, roomba_command, request_device_state_update=True)

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called.")
        self._request_devices_state()

    def isConnected(self, connection, reconnect=True):
        if connection is not None:
            Domoticz.Debug("Connection is alive." + str(connection.Name))
            if connection.Connecting():
                Domoticz.Debug("rest980 Connecting...")
            elif connection.Connected():
                Domoticz.Debug("rest980 Connected.")
                return True
            else:
                connection.Connect()
        elif reconnect:
            Domoticz.Debug("No connection creating new one.")
            self.InitializeREST980Connection()
        return False

    def _get_dev_id(self, key):
        return self.UNITS[key][0]

    def _get_dev(self, key):
        return Devices[self._get_dev_id(key)]

    def _sent_message(self, connection, command, request_device_state_update=True):
        Domoticz.Debug("_sent_message: " + str(command) + " connection: " + str(connection))
        if self.isConnected(connection):
            self.send_data['URL'] = self.rest_api.get_local_url(command)
            Domoticz.Debug("_sent_message: " + str(self.send_data['URL']))
            connection.Send(self.send_data)
            Domoticz.Debug("_sent_message: post Send, request_device_state_update: " + str(request_device_state_update))
            if request_device_state_update:
                self._wait_for_update = True
        else:
            self.que.put(command)

    def _request_devices_state(self, connection=None):
        l_con = connection if connection else self.http_conn
        Domoticz.Debug("_request_devices_state: " + str(l_con))
        self._sent_message(connection=l_con, command="state", request_device_state_update=False)


global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def dump_http_response_to_log(httpResp, level=0):
    if (level==0): Domoticz.Debug("HTTP Details ("+str(len(httpResp))+"):")
    indentStr = ""
    for x in range(level):
        indentStr += "----"
    if isinstance(httpResp, dict):
        for x in httpResp:
            if not isinstance(httpResp[x], dict) and not isinstance(httpResp[x], list):
                Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")
            else:
                Domoticz.Debug(indentStr + ">'" + x + "':")
                dump_http_response_to_log(httpResp[x], level + 1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            Domoticz.Debug(indentStr + "['" + x + "']")
    else:
        Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")

def update_device(unit,
                  n_value=-1, s_value="", image_id=-1, sig_lvl=-1, bat_lvl=-1, opt={}, timed_out=-1, name="",
                  type_name="", type=-1, sub_type=-1, switch_type=-1, used=-1, descr="", color="", supp_trigg=-1):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    Domoticz.Debug("update_device unit:" + str(unit))
    if unit in Devices:
        args = {}
        # Must always be passed for update
        if n_value != -1:
            args["nValue"] = n_value
        else:
            args["nValue"] = Devices[unit].nValue
        s_value = str(s_value)
        if len(s_value) > 0:
            args["sValue"] = s_value
        else:
            args["sValue"] = Devices[unit].sValue

        Domoticz.Debug(str(args))
        # Optionals
        if image_id != -1:
            args["Image"] = image_id
        if sig_lvl != -1:
            args["SignalLevel"] = sig_lvl
        if bat_lvl != -1:
            args["BatteryLevel"] = bat_lvl
        opt = str(opt)
        if len(opt) > 0:
            args["Options"] = opt
        if timed_out != -1:
            args["TimedOut"] = timed_out
        name = str(name)
        if len(name) > 0:
            args["Name"] = name
        type_name = str(type_name)
        if len(type_name) > 0:
            args["TypeName"] = type_name
        if type != -1:
            args["Type"] = type
        if sub_type != -1:
            args["Subtype"] = sub_type
        if switch_type != -1:
            args["Switchtype"] = switch_type
        if used != -1:
            args["Used"] = used
        descr = str(descr)
        if len(descr) > 0:
            args["Description"] = descr
        color = str(color)
        if len(color) > 0:
            args["Color"] = color
        if supp_trigg != -1:
            args["SuppressTriggers"] = supp_trigg
        Domoticz.Debug("Update with " + str(args))
        Devices[unit].Update(**args)
    else:
        global _plugin
        _plugin.CreateDevices()


def update_dict(dict_to_update, key, dict):
    if key in dict_to_update.keys():
        dict_to_update[key].update(dict)
    else:
        dict_to_update[key] = dict
