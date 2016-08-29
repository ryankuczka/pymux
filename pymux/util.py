import click
import os
import pipes
import shlex
import subprocess


class TmuxError(Exception):
    pass


class TmuxObj(object):
    def __init__(self, tmux_cmd='tmux', debug=False):
        self.tmux_cmd = tmux_cmd
        self.debug = debug

    def _tmux_exe(self, cmd, **kwargs):
        if self.debug:
            click.echo(('' if 'has-session' in cmd else '\t') +
                self.tmux_cmd + ' ' + cmd)
            return 0, '', ''

        cmd = [self.tmux_cmd] + shlex.split(cmd)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs
        )
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr


class TmuxWindow(TmuxObj):
    def __init__(self, session, id, window_config, **kwargs):
        self.session = session
        self.id = id
        self.name = window_config['name']
        self.panes = window_config['panes']
        self.layout = window_config.get('layout', 'even-vertical')

        super(TmuxWindow, self).__init__(**kwargs)

    def create(self):
        cmd = ('new-window '
            '-c {self.session.root_dir} '
            '-t {self.session.session_name}:{self.id} '
            '-n {self.name}').format(self=self)
        self._tmux_exe(cmd)

        self.create_panes()
        self.run_cmds()

    def create_panes(self):
        for i in range(len(self.panes) - 1):
            cmd = 'splitw -t {self.session.session_name}:{self.id}'.format(self=self)
            self._tmux_exe(cmd)

        cmd = 'select-layout -t {self.session.session_name}:{self.id} {self.layout}'.format(self=self)
        self._tmux_exe(cmd)

    def run_cmds(self):
        for i, pane_cmds in enumerate(self.panes):
            if isinstance(pane_cmds, basestring):
                pane_cmds = [pane_cmds]

            for pane_cmd in pane_cmds:
                cmd = ('send-keys '
                    '-t {self.session.session_name}:{self.id}.{pane_id} '
                    '{pane_cmd} C-m').format(self=self, pane_id=i + 1, pane_cmd=pipes.quote(pane_cmd))
                self._tmux_exe(cmd)

    def rename(self):
        cmd = 'rename-window -t {self.session.session_name}:{self.id} {self.name}'.format(self=self)
        self._tmux_exe(cmd)


class TmuxSession(TmuxObj):

    def __init__(self, session_name, root_dir='', windows=None, **kwargs):
        self.session_name = session_name
        self.root_dir = root_dir
        self.window_configs = [{'name': 'default', 'panes': []}] if windows is None else windows
        self.windows = []

        super(TmuxSession, self).__init__(**kwargs)

    def kill(self):
        cmd = 'kill-session -t {}'.format(self.session_name)
        self._tmux_exe(cmd)

    def exists(self):
        cmd = 'start-server; has-session -t {}'.format(self.session_name)
        returncode, stdout, stderr = self._tmux_exe(cmd)
        return returncode == 0

    def attach(self):
        cmd = '-u attach-session -t {}'.format(self.session_name)
        self._tmux_exe(cmd)

    def switch(self):
        cmd = '-u switch-client -t {}'.format(self.session_name)
        self._tmux_exe(cmd)

    def create(self):
        cmd = 'new-session -d -s {self.session_name} -c {self.root_dir}'.format(self=self)
        env = os.environ.copy()
        env.pop('TMUX', None)
        self._tmux_exe(cmd, env=env)

        window = TmuxWindow(self, 1, self.window_configs[0], tmux_cmd=self.tmux_cmd, debug=self.debug)
        window.rename()
        window.create_panes()
        window.run_cmds()
        self.windows.append(window)

        self.create_windows()

    def create_grouped(self, target_session):
        cmd = 'new-session -s {self.session_name} -t {target_session}'.format(self=self, target_session=target_session)
        env = os.environ.copy()
        env.pop('TMUX', None)
        self._tmux_exe(cmd, env=env)

    def create_windows(self):
        for i, window_config in enumerate(self.window_configs[1:]):
            window = TmuxWindow(self, i + 2, window_config, tmux_cmd=self.tmux_cmd, debug=self.debug)
            window.create()
            self.windows.append(window)

        cmd = 'select-window -t 1'
        self._tmux_exe(cmd)
