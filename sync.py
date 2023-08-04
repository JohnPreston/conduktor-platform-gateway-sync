#!/usr/bin/env python

"""
GW Bootstrap endpoint
GW API Endpoint
GW Username/Password
Platform API Key
"""

from __future__ import annotations

import re
from argparse import ArgumentParser

from cdk_proxy_api_client.proxy_api import ApiClient, ProxyClient
from cdk_proxy_api_client.admin_auth import AdminAuth
from cdk_proxy_api_client.tenant_mappings import Multitenancy
from conduktor_public_api_client.client import AuthenticatedClient
from conduktor_public_api_client.api.cluster import (
    list_all_clusters,
    create_or_update_a_cluster,
)
from conduktor_public_api_client.models.upsert_shared_cluster_request import (
    UpsertSharedClusterRequest,
)

import jwt


PASSWORD_FIND = re.compile(r"(?:password=(?:\'|\"))(?P<password>[\S]+)(?:\'|\")")


def set_parser():
    parser = ArgumentParser()
    parser.add_argument("--platform-url", type=str, required=True)
    parser.add_argument("--platform-api-key", type=str, required=True)
    parser.add_argument("--gw-url", type=str, required=True)
    parser.add_argument("--gw-bootstrap-servers", type=str, required=True)
    parser.add_argument("--gw-api-username", type=str, required=True)
    parser.add_argument("--gw-api-password", type=str, required=True)
    parser.add_argument("--tenant-jwt-lifetime", type=int, default=(90 * 24 * 3600))
    return parser


def get_tenant_details_from_token(jwt_token: str) -> dict:
    """Uses existing secret JWT token to identify tenant owner"""
    try:
        jwt_content = jwt.decode(
            jwt_token,
            options={"verify_signature": False},
            algorithms=["HS256", "HS384", "HS512"],
        )
        return jwt_content
    except Exception as error:
        print(error)
        raise


def set_proxy_client(url: str, username: str, password: str) -> ProxyClient:
    _api = ApiClient(url=url, username=username, password=password)
    return ProxyClient(_api)


def gen_cluster_properties(tenant_name: str, password: str) -> str:
    props = """client.id=CONDUKTOR_PLATFORM_{}
security.protocol=SASL_SSL
sasl.mechanism=PLAIN
default.api.timeout.ms=10000
request.timeout.ms=5000
acks=all
sasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required username='{}' password='{}';
""".format(
        tenant_name, tenant_name, password
    )

    return props


def set_update_tenants_in_platform(
    proxy_client: ProxyClient,
    gw_bootstrap_servers: str,
    platform_url: str,
    platform_api_key: str,
    jwt_token_lifetime: int,
) -> None:
    tenants_req = Multitenancy(proxy_client).list_tenants()
    tenants = tenants_req.json()["tenants"]
    auth_client = AdminAuth(proxy_client)
    with AuthenticatedClient(
        base_url=platform_url,
        token=platform_api_key,
        headers={"User-Agent": "conduktor/sync-script"},
    ) as platform_client:
        clusters = list_all_clusters.sync(client=platform_client)
        for _tenant in tenants:
            new_jwt = auth_client.create_tenant_credentials(
                _tenant, token_lifetime_seconds=jwt_token_lifetime, token_only=True
            )
            for _cluster in clusters:
                if _tenant == _cluster.technical_id or _tenant == _cluster.name:
                    create_or_update_a_cluster.sync(
                        _tenant.replace(".", ""),
                        client=platform_client,
                        json_body=UpsertSharedClusterRequest(
                            bootstrap_servers=_cluster.bootstrap_servers,
                            name=_cluster.name,
                            properties=gen_cluster_properties(_tenant, new_jwt),
                        ),
                    )
                    print("Updated cluster {} for tenant {}".format(_cluster.technical_id, _tenant))
                    break
            else:
                new_cluster_props = gen_cluster_properties(_tenant, new_jwt)
                new_cluster_body = UpsertSharedClusterRequest(
                        name=_tenant,
                        bootstrap_servers=gw_bootstrap_servers,
                        properties=new_cluster_props,
                    )
                cluster = create_or_update_a_cluster.sync(
                    _tenant.replace(".", ""),
                    client=platform_client,
                    json_body=new_cluster_body,
                )
                print(
                    "Created {} cluster for tenant {}".format(
                        cluster.technical_id, _tenant
                    )
                )


def main():
    _PARSER = set_parser()
    _ARGS = _PARSER.parse_args()
    _PROXY = set_proxy_client(
        _ARGS.gw_url, _ARGS.gw_api_username, _ARGS.gw_api_password
    )
    set_update_tenants_in_platform(
        _PROXY,
        _ARGS.gw_bootstrap_servers,
        _ARGS.platform_url,
        _ARGS.platform_api_key,
        _ARGS.tenant_jwt_lifetime,
    )


if __name__ == "__main__":
    main()
