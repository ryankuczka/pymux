# pymux

Python powered, JSON configured, tmux manager

# Installation

```bash
git clone https://github.com/ryankuczka/pymux
cd pymux
python setup.py install
```

# Usage

```
> pymux --help
Usage: pymux [OPTIONS] COMMAND [ARGS]...

  Manage tmux sessions with ease!

Options:
  -c, --config KEY VALUE  Specify a KEY: VALUE pair to override config
  --help                  Show this message and exit.

Commands:
  config  Print the current config to stdout.
  create  Create a new pymux project and open its...
  debug   Print out the commands that will be run on...
  delete  Delete a project.
  edit    Open an existing project's config file for...
  kill    Kill a running session.
  list    List all existing projects.
  start   Start a project's tmux session or switch to...
```
