# snekcfg

`snekcfg` is a minimalist wrapper over `configparser` that offers a more
streamlined user experience. Expected options and their types are predefined
to prevent errors and minimize repetative logic within your codebase. This
allows for simple, direct access to your configuration within your program
without worrying about typos or type conversion.

**example.py**

```python
import snekcfg

cfg = snekcfg.Config('snek.cfg')

sct = cfg.section('server')
sct.init('host', default='127.0.0.1')
# automatically typed as an int
sct.init('port', default=1337)

# already built-in, but here as an example
users = {'graham', 'john', 'terryg', 'eric', 'terryj', 'michael'}
cfg.register_type(set[str],
    encode=lambda v: ','.join(v),
    decode=lambda v: set(x.strip() for x in v.split(',')))

cfg.init('whitelist.users', default=users, type=set[str])

 # writes to 'snek.cfg'
cfg.write()

# new instance
cfg = snekcfg.Config('snek.cfg')
cfg.read()

assert cfg['server.port']) == 1337
assert cfg.section('whitelist')['users'] == users
```

**snek.cfg**

```ini
[server]
host = 127.0.0.1
port = 1337

[whitelist]
users = graham,john,terryg,eric,terryj,michael
```
