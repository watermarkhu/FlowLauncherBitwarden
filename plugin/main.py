
from flox import Flox
from flox.clipboard import Clipboard 
import subprocess, json, os
import favicon, validators, webbrowser
import pathlib, tempfile
import urllib.request
from requests.exceptions import HTTPError, SSLError, ConnectionError
from urllib.error import HTTPError as URLError


NO_WINDOW = 0x08000000
TMPDIR = pathlib.Path(tempfile.gettempdir())
DEFAULT_ICON = pathlib.Path(__file__).parent.parent.absolute() / 'icons' / 'bitwarden256x256.png'


# have your class inherit from Flox
class Bitwarden(Flox, Clipboard):

    def query(self, query):

        if not self.settings['bw_session']:
            self.add_item(
                title='Please provide the session key in the settings.',
                method=self.open_url,
                parameters=['https://bitwarden.com/help/cli/']
            )
            return self._results
        
        if len(query) > 1:

            my_env = os.environ.copy()
            my_env['BW_SESSION'] = self.settings['bw_session']

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            if query == 'sync':
                subprocess.run('bw sync'.split(), env=my_env, startupinfo = startupinfo)
                self.add_item(
                        title='Sync completed'
                    )

            try:
                output = subprocess.run(f'bw list items --search {query}'.split(), capture_output=True, env=my_env, startupinfo = startupinfo)
                outputStr = output.stdout.decode('UTF-8')
                outputDict = json.loads(outputStr);
            except json.JSONDecodeError:
                self.add_item(
                    title='Wrong session key provided in settings'
                )
            else:
                outputDict = [item for item in outputDict if 'login' in item.keys()]

                if len(outputDict) == 0:
                    self.add_item(
                        title='No entries found'
                    )
                else:
                    for i in range(len(outputDict)):
                        
                        item = outputDict[i]

                        if type(item['login']['uris']) is list:
                            urls = [uriItem['uri'] for uriItem in item['login']['uris'] if validators.url(uriItem['uri'])]

                        if len(urls) != 0:

                            fileName = ''.join(e for e in item["name"] if e.isalnum())
                            iconPath = TMPDIR / f'{fileName}.png'
                            if not os.path.exists(iconPath):
                                try:
                                    icon = favicon.get(urls[0])[0]
                                    urllib.request.urlretrieve(icon.url, iconPath)
                                except (HTTPError, SSLError, URLError, IndexError,ConnectionError) as e:
                                    iconPath = DEFAULT_ICON
                        else:
                            iconPath = DEFAULT_ICON
                                
                        self.add_item(
                            title=item['name'],
                            subtitle=item['login']['username'],
                            icon=iconPath,
                            method=self.type_char,
                            parameters=[item['login']['password']],
                            context = [
                                item['login']['username'],
                                item['login']['password'], 
                                item['login']['totp'],
                                item.get('fields', []),
                                urls,
                                str(iconPath)
                            ]
                        )

    def type_char(self, char):
        """
        Type a character into the current focused window.
        """
        script_path = pathlib.Path(__file__).parent.resolve() / "sendkeys.py"
        self.put(char)
        python_path = 'pythonw.exe'
        python_setting = pathlib.Path(self.app_settings["PluginSettings"].get("PythonDirectory"))
        if python_setting:
            python_path = pathlib.Path(python_setting, "python.exe")
        subprocess.Popen([python_path, script_path], creationflags=NO_WINDOW)
        self.close_app()

    def open_url(self, url):
        webbrowser.open(url)
        self.close_app()

    def context_menu(self, data):
        self.add_item(
            title='Username',
            subtitle=data[0],
            icon=data[5],
            method=self.type_char,
            parameters=[data[0]]
        )
        self.add_item(
            title='Password',
            subtitle='Hidden',
            method=self.type_char,
            icon=data[5],
            parameters=[data[1]]
        )
        if data[2] != None:
            self.add_item(
                title='TOTP',
                subtitle=data[2],
                icon=data[5],
                method=self.type_char,
                parameters=[data[2]]
            )
        for field in data[3]:
            if field['type'] == 1:
                self.add_item(
                    title=field['name'],
                    subtitle='Hidden',
                    icon=data[5],
                    method=self.type_char,
                    parameters=[field['value']]
                )
            else:
                self.add_item(
                    title=field['name'],
                    subtitle=field['value'],
                    icon=data[5],
                    method=self.type_char,
                    parameters=[field['value']]
                )
        for url in data[4]:
            self.add_item(
                title='Open in browser',
                subtitle=url,
                icon=data[5],
                method=self.open_url,
                parameters=[url]
            )

        