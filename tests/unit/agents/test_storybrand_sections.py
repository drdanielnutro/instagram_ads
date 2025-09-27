from app.agents.storybrand_sections import build_storybrand_section_configs


def test_storybrand_section_configs_have_unique_keys():
    configs = build_storybrand_section_configs()
    keys = [cfg.state_key for cfg in configs]
    assert len(configs) == 16
    assert len(set(keys)) == len(keys)
