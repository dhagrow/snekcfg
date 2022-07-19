`snekcfg` is a minimalist wrapper over
[configparser](https://docs.python.org/3/library/configparser.html) that offers
a more streamlined user experience.

Expected options and their types are predefined to prevent errors and minimize
repetative logic within your codebase. This allows for simple, direct access to
your configuration within your program without worrying about typos or type
conversion.

## example.py

```python
import snekcfg

cfg = snekcfg.Config('example.cfg')

sct = cfg.section('server')
# the default value is used to automatically type as an int
sct.init('port', 8080)
# or, you can be explicit
sct.init('host', default='127.0.0.1', type=str)

print(cfg)
print(sct)

# some common types like set[str] are already built-in,
# but here is an example of adding codecs for a new type
# *type* can be a type object, or just a string like 'str_set'
def decode(v):
    x = set((x.strip() for x in v.split(',')) if v else set())
    print((v, x))
    return x
cfg.register_type(
    type=set[str],
    encode=lambda v: ','.join(v),
    decode=decode)


# sections can be accessed using dot notation (one level deep)
cfg.init('users.whitelist', default=set(), type=set[str])

# update values with dot notation
users = {'graham', 'john', 'terryg', 'eric', 'terryj', 'michael'}
cfg['users.whitelist'].update(users)
# or through the section
cfg.section('server')['port'] = 1337

# write to 'example.cfg'
cfg.write()

# clear changes, reset defaults
cfg.clear()

assert cfg['server.port'] == 8080
assert cfg['users.whitelist'] == set()

# read from 'example.cfg'
cfg.read()

# types are preserved
assert cfg['server.port'] == 1337
assert cfg['users.whitelist'] == users, cfg['users.whitelist']
```

## example.cfg

```ini
[server]
host = 127.0.0.1
port = 1337

[users]
whitelist = eric,graham,michael,john,terryg,terryj
```
