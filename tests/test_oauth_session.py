"""Tests for portal pool discovery parsing."""

from custom_components.norsup_smartpool.api.oauth_session import parse_pools_from_pool_data

POOL_A = "833f31e4-54c7-4101-8ba3-0763b42cfd12"
POOL_B = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_parse_pools_from_pool_data() -> None:
    text = (
        f'[{{"id":"{POOL_A}","name":"Backyard"}},'
        f'"{{POOL_A}}","Garden pool",'
        f'"{{POOL_B}}","Holiday home"]'
    )
    # Real /pool.data embeds uuid,name pairs in CSV-like fragments
    text = f'fragment,"{POOL_A}","Garden pool",more,"{POOL_B}","Holiday home",end'
    pools = parse_pools_from_pool_data(text)
    assert len(pools) == 2
    assert pools[0].pool_id == POOL_A
    assert pools[0].name == "Garden pool"
    assert pools[1].pool_id == POOL_B
