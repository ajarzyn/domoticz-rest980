# domoticz-rest980
Inspired by damsma/rest980-domoticz (https://github.com/damsma/rest980-domoticz) this is plugin to control iRobot based on koalazak/rest980 (https://github.com/koalazak/rest980).

Instructiuons:
<h1>1. Install rest980</h1>
Use instruction from the rest980 repository.
Install, run and test it.

If you prefere to use docker image of rest980:
At the day I'm writting this README pull request(https://github.com/koalazak/rest980/pull/53) isn't marged yet.
But you can download  <a hreaf="https://github.com/koalazak/rest980/pull/53/commits/d1c952253db79ba0a3f95fceb1dc52165268711f#diff-78503ae7c423923966b2b4dda7ab3fb5">dockerCreate.sh</a>,
update required fields and have you docker builded automatically. Refere to README update in same commit.

<h1>2. Install this plugin</h1>
Install plugin in python plugins directory for domoticz.
<pre><code>
git clone https://github.com/koalazak/rest980/pull/53/commits/d1c952253db79ba0a3f95fceb1dc52165268711f#diff-78503ae7c423923966b2b4dda7ab3fb5
</code></pre>
Restart domoticz.

<h1>3. Configure the plugin</h1>
Go to Setup -> Hardware -> Type -> iRobot based on rest980 -> Fill options -> Add

<h1>Option explanation</h1>
Name is just for domoticz db - Devices names will be updated with iRobot name.
IP and PORT - are parameters to connect with rest980
Display battery status - will update Devices names with baterry charge value at the end of the name.
Debug - in case of any problem try to rise log level.

