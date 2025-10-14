# my_house_energy_consumption
Some Stuff on Getting My Energy Consumption

## Getting Energy Consumption Data From Tibber

### Getting access

1. Go to: https://developer.tibber.com/settings/access-token
2. Log in with your Tibber account
3. Create a new token or copy your existing token.


### Setup

```shell
uv sync
```

### run
```shell
uv run python tibber_collector.py
```