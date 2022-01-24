# Introduction
Open source release of Geazer SB, a private kinda selfbot.
Why? Because I don't want to work on it anymore, Discord is patching shit and I don't want the code to completely die.
A lot of this code probably won't work (like sending embeds isn't possible with user accounts anymore), but use whatever you want.

The difference between this and the paid version is that this one has the auth and check shit removed, as well as API tokens (that need to be set to use applicable commands) in `src/cogs/utils/tokens.py`

Note that most code is written badly (no comments, barely any whitelines, bad readability) mostly due to a restriction my obfuscation tool placed on the size a file can be and also because this has always been a solo project and never required good readability for others.

# Setup
+ Install Python 3.8.5 __and add to PATH!__:
  * Windows: https://www.python.org/ftp/python/3.8.5/python-3.8.5-amd64.exe
  * MacOS: https://www.python.org/ftp/python/3.8.5/python-3.8.5-macosx10.9.pkg
  * Ubuntu/Linux: https://linuxize.com/post/how-to-install-python-3-8-on-ubuntu-18-04/
+ Install the requirements:
  * Windows: Run install.bat as administrator
  * MacOS/Ubuntu/Linux: run `python3.8 -m pip install -r requirements.txt` in the selfbots directory
+ Launch the selfbot:
  * Windows: Run run.bat as administrator
  * MacOS/Ubuntu/Linux: run `python3.8 main.py` in the selfbots directory

+ Website: https://geazersb.github.io