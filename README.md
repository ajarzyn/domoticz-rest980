# domoticz-rest980
Inspired by [damsma/rest980-domoticz](https://github.com/damsma/rest980-domoticz) this is plugin to control iRobot based on [koalazak/rest980](https://github.com/koalazak/rest980).

## Instruction:
### 1. Install rest980
Use instruction from the [koalazak/rest980](https://github.com/koalazak/rest980) repository.
Install, run and test it, in case of any problems refere to rest980 help.

#### If you prefere to use docker image of rest980:
> In case that docker doesn't work add port binding at container creation `-p $PORT_YOU_WANT_TO_USE:3000`

At the day I'm writting this README [pull request](https://github.com/koalazak/rest980/pull/53) isn't marged yet.
But you can download [dockerCreate.sh](https://github.com/koalazak/rest980/pull/53/commits/d1c952253db79ba0a3f95fceb1dc52165268711f#diff-78503ae7c423923966b2b4dda7ab3fb5),
update required fields and have you docker builded automatically. Refere to README update in that commit.

### 2. Install this plugin
Install plugin in python plugins directory for domoticz.
```bash
git clone https://github.com/ajarzyn/domoticz-rest980.git
```
Restart domoticz.

### 3. Configure the plugin
Go to Setup -> Hardware -> Type -> iRobot based on rest980 -> Fill options -> Add

### Option explanation
Name is just for domoticz db - Devices names will be updated with iRobot name.
IP and PORT - are parameters to connect with rest980
Display battery status - will update Devices names with baterry charge value at the end of the name.
Debug - in case of any problem try to rise log level.

