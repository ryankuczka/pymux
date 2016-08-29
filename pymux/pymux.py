import click
import json
import shlex
import subprocess
import os

from .util import TmuxSession


class Project(click.ParamType):
    name = 'PROJECT'

    def convert(self, value, param, ctx):
        config = ProjectConfig()
        config['name'] = value
        if os.path.isfile(config.path):
            return value
        self.fail('{0} does not exist. Create it with \'pymux create {0}\''.format(value))


class ProjectConfig(dict):
    config_template = """{{
    "name": {name},
    "root": {root},
    "socketName": {socketName},
    "preCmd": {preCmd},
    "winPreCmd": {winPreCmd},
    "tmuxCmd": {tmuxCmd},
    "tmuxOpts": {tmuxOpts},
    "windows": {windows}
}}"""

    def __init__(self, *args, **kwargs):
        self.config_dir = click.get_app_dir('pymux', force_posix=True)
        if not os.path.isdir(self.config_dir):
            os.mkdir(self.config_dir)

        self.default_windows = [
            {'name': 'editor', 'panes': ['vim']},
            {'name': 'shell', 'panes': []},
        ]

        super(ProjectConfig, self).__init__(*args, **kwargs)

    @property
    def path(self):
        """ Returns the path to the project's config """
        return os.path.join(self.config_dir, self['name'] + '.json')

    def create(self):
        """ Creates a new project config """
        with open(self.path, 'w') as f:
            f.write(self.config_template.format(
                name=json.dumps(self['name']),
                root=json.dumps(self.get('root', '~/{}'.format(self['name']))),
                socketName=json.dumps(self.get('socketName', '')),
                preCmd=json.dumps(self.get('preCmd', '')),
                winPreCmd=json.dumps(self.get('winPreCmd', '')),
                tmuxCmd=json.dumps(self.get('tmuxCmd', 'tmux')),
                tmuxOpts=json.dumps(self.get('tmuxOpts', '')),
                windows=json.dumps(self.get('windows', self.default_windows)),
            ))

    def delete(self):
        """ Deletes the project """
        os.remove(self.path)

    def load(self):
        """ Load JSON config from disk """
        # Only update values that don't already exist
        with open(self.path, 'r') as f:
            file_config = json.load(f)
        for key, val in file_config.items():
            if key not in self:
                self[key] = val

    def save(self):
        """ Save JSON config to disk """
        with open(self.path, 'w') as f:
            f.write(self.config_template.format(
                name=json.dumps(self['name']),
                root=json.dumps(self['root']),
                socketName=json.dumps(self['socketName']),
                preCmd=json.dumps(self['preCmd']),
                winPreCmd=json.dumps(self['winPreCmd']),
                tmuxCmd=json.dumps(self['tmuxCmd']),
                tmuxOpts=json.dumps(self['tmuxOpts']),
                windows=json.dumps(self['windows']),
            ))


pass_config = click.make_pass_decorator(ProjectConfig, ensure=True)


@click.group(help='Manage tmux sessions with ease!')
@click.option('--config', '-c', 'config_overrides', multiple=True, nargs=2, metavar='KEY VALUE', help='Specify a KEY: VALUE pair to override config')
@pass_config
def pymux(config, **options):
    for key, val in options['config_overrides']:
        try:
            config[key] = json.loads(val)
        except ValueError:
            config[key] = val


@pymux.command(help='Print the current config to stdout.')
@click.argument('project', type=Project())
@pass_config
def config(config, project):
    config['name'] = project
    config.load()
    click.echo(json.dumps(config, indent=2))


@pymux.command(help='Create a new pymux project and open its config file for editing.')
@click.argument('project')
@pass_config
def create(config, project):
    config['name'] = project
    config.create()

    subprocess.call(shlex.split(os.environ['EDITOR']) + [config.path])


@pymux.command(help='Open an existing project\'s config file for editing.')
@click.argument('project', type=Project())
@pass_config
def edit(config, project):
    config['name'] = project
    config.load()
    config.save()

    subprocess.call(shlex.split(os.environ['EDITOR']) + [config.path])


@pymux.command(help='Delete a project.')
@click.argument('project', type=Project())
@pass_config
def delete(config, project):
    config['name'] = project
    if click.confirm('Are you sure you want to delete \'{0}\'?'.format(config['name'])):
        config.delete()


@pymux.command(help='List all existing projects.')
@pass_config
def list(config):
    click.echo('Available Projects:')
    for filename in os.listdir(config.config_dir):
        click.echo('\t' + filename.replace('.json', ''))


@pymux.command(help='Kill a running session. Convenience for \'tmux kill-session\'')
@click.argument('project', type=Project())
@pass_config
def kill(config, project):
    config['name'] = project
    config.load()

    session = TmuxSession(config['name'])
    if session.exists():
        session.kill()


@pymux.command(help='Start a project\'s tmux session or switch to it if it already exists.')
@click.argument('project', type=Project())
@click.option('-g', '--group', is_flag=True, help='Start a new grouped session.')
@pass_config
def start(config, project, group):
    config['name'] = project
    config.load()

    session_name = config['name'] if not group else config['name'] + '1'

    session = TmuxSession(session_name, config['root'],
        windows=config['windows'], tmux_cmd=config['tmuxCmd'])

    if not session.exists():
        if group:
            session.create_grouped(config['name'])
        else:
            session.create()

    if os.environ.get('TMUX'):
        session.switch()
    else:
        session.attach()


@pymux.command(help='Print out the commands that will be run on \'start\'.')
@click.argument('project', type=Project())
@pass_config
def debug(config, project):
    config['name'] = project
    config.load()

    session = TmuxSession(config['name'], config['root'],
        windows=config['windows'], tmux_cmd=config['tmuxCmd'],
        debug=True)

    session.exists()

    click.echo('\n# Create session if it doesn\'t exist.\nif [[ $? -eq 1]]; then')
    session.create()
    click.echo('fi')

    click.echo('\nif [[ -z $TMUX ]]; then\n\t# Attach to the session.')
    session.attach()
    click.echo('else\n\t# If already inside a tmux session, switch to it instead.')
    session.switch()
    click.echo('fi')


if __name__ == '__main__':
    pymux()
