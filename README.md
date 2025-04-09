<h1>About Blasty:</h1>

It started as a script to profile and play around with blamcon light guns but has turned into a full-blown game output handler.
Currently connects to the network outputs from MAME and Demulshooter. Can leave it running or load per game, it should adjust based on processes it can see. It
translates outputs into serial commands and relays those to the device. It's currently just proof of concept so expect bugs. Written in python so should run anywhere python is supported.

<h2>Features</h2>
Devices are configured with profiles, you can name the profiles whatever you want. Configuration files will be put in a folder named after the profile name. A game may have configuration files in multiple profiles allowing you to configure how each device attached to that profile responds to the outputs. <br>
Each device maintains its own queue. Outputs are broadcast to all connected devices allowing devices respond to configured outputs.

Variable Token replacements supported in output chains:<br>

<li>#s# = current value of output</li>
<li>#HEX... = converts hex to integer</li>
<li>#VAR... = replace ... with a custom variable name you want to use to track values of an output</li>
<li>#MAX... = used with VAR, replace ... with the same variable to get the max value of the currently tracked series</li>
<li>#MIN... = used with VAR, replace ... with the same variable to get the min value of the currently tracked series</li>
<li>#CLW...:......# = used with VAR, replace ... with the same variable and any number of hex color codes prefixed with ":" to create a color transition wheel for setting led colors based off the value in the variable.<br>
example:
#CLWAMMO:00FF00:FFFF00:FF0000#</li>

Action Token replacements supported in output chains:<br>
<li>%RMP..TO..% =  remaps a value to a different value</li>
<li>%EVL...% = allows a mathematical equation to be evaluated to change value
example of cycling between value 1,2 and 3 based on current value: %EVL#s#MOD3+1%</li>
<li>%RVL...% = replaces itself with the result of a mathematical equation</li>

Timing commands supported in  output chains:
<li>%WAIT…% = will make a pause between commands. This also pauses the queue so waiting too much can expire some commands.</li>
<li>%TIME…% = will make anything after it go into a timeout queue where it will be added back into the process queue when the time is up to resume. This does not prevent the queue from processing like wait.</li>  
<li>%TIMR…% = is like TIME but with a refresh. Whatever follows it will go back into the queue when the timer expires, but if the command is queued again before that happens it will refresh the timer. Used for turning off stuff after a repeated commands. NOTE: this will not work if any dynamic commands are used after it in the chain.</li>  

<h2>Program Configuration</h2>

Default configuration file "blasty.ini" will be created on first run next to the program. Device player id's, profile and connection settings are configured here for each device you want connected. Other options will be here if they enable something per device. Output monitoring for example.

<h2>Game Configuration</h2>

Default configuration files are created in the config folder as well as each profile folder. Game configuration files are created automatically in the config folder only and serve as starting templates. The first time you play a game the default settings will be used to make the game configuration file and then any outputs it receives without default configurations will be added to the outputs section as well as all value positions monitored; commited out and ready to configure. Game configuration files in profiles need to be manually created. The default.ini settings will be used if no game specific configuration file is in the profile/directory.


Blasty uses ini files and requires serial commands to be defined.

example:

P1_CtmRecoil=|FB.0.1+

Each output coming from the game has a name and a value. Each possible value for a given name will be separated by a "|". These values will be tied to serial commands that are sent to the device.
So in the above example a value of 0 will send nothing but a value of 1 will send "FB.0.1+" to the configured device. Multiple commands can be added for a value using a ',' as seperator.


To make things easier token replacement can be used.

example:

P1_CtmRecoil=|%RECOIL%<br>
P2_CtmRecoil=|%P1_CtmRecoil%

or even better:

RECOIL=|FB.0.1+

P1_CtmRecoil=|%RECOIL%<br>
P2_CtmRecoil=|%RECOIL%

When either P1_CtmRecoil or P2_CtmRecoil has value 1 it will use what RECOIL has for value 1. Note that if a token replacement is used it still uses the command at that value. If P1_CtmRecoil or P2_CtmRecoil has a 0 value there is no token replacement for that value in the above example.

If a value is read beyond what is configured it will use the last value. So for example:


P1_Ammo=|CM.26.1+FB.1.1+

If an output of "P1_Ammo" has a value of 10 it will use the last value configured which would be 1. Because of this behavior we have a couple special tokens that adjust the value. RMP,EVL,RVL allow modifying value or current command at the value.




