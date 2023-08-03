# Syn Conduktor Gateway tenants with Conduktor Platform

Requirements:

* Conduktor GW with API enabled for tenants
* Conduktor Platform 1.17 + with API Key

## Execute

create a bash env file (i.e. `.my_config`) and set environment variables to match the command

```bash
source .my_config
python sync.py \
  --platform-api-key $_API_KEY \
  --platform-url $PLATFORM_URL \
  --gw-bootstrap-servers $GW_BOOTSTRAP_SERVERS \
  --gw-url $GW_API_ENDPOINT \
  --gw-api-username $GW_API_USERNAME \
  --gw-api-password $GW_API_PASSWORD
```
