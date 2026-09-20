from app import experiment as ex
from app import experiment_stats as st


def test_arms_are_stable_roughly_even_and_carry_their_ablations():
    arms = [{"name": "control", "ablations": []}, {"name": "no_memory", "ablations": ["rejection_memory"]}]
    picks = [ex.assign_arm(f"r{i}", arms)["name"] for i in range(2000)]
    assert picks == [ex.assign_arm(f"r{i}", arms)["name"] for i in range(2000)]
    assert 0.45 < picks.count("control") / 2000 < 0.55
    request = ex.with_arm({"arms": arms}, "r1")
    assert request["arm"] in {"control", "no_memory"} and isinstance(request["ablations"], list)


def test_a_different_salt_reshuffles_assignment():
    arms = [{"name": "a"}, {"name": "b"}]
    assert [ex.assign_arm(f"r{i}", arms, "x")["name"] for i in range(50)] != [ex.assign_arm(f"r{i}", arms, "y")["name"] for i in range(50)]


def test_only_known_ablations_count_and_context_records_conditions():
    assert ex.disabled({"ablations": ["autofill", "nonsense"]}) == {"autofill"}
    c = ex.context({"arm": "x", "generation": {"temperature": 0.2, "seed": 7}}, model="q", record_id="r", code_version="1", prompt_version="p")
    assert (c["arm"], c["temperature"], c["seed"], c["model_version"]) == ("x", 0.2, 7, "q")


def test_gold_set_is_a_stable_small_share():
    picks = [ex.is_gold(f"r{i}") for i in range(4000)]
    assert picks == [ex.is_gold(f"r{i}") for i in range(4000)] and 0.03 < sum(picks) / 4000 < 0.07


def test_wilson_interval_is_sane_at_the_edges():
    assert st.wilson(0, 0)["rate"] is None
    hi = st.wilson(10, 10)
    assert hi["high"] == 1.0 and 0.6 < hi["low"] < 0.8
    mid = st.wilson(50, 100)
    assert mid["low"] < 0.5 < mid["high"]


def test_bootstrap_is_reproducible():
    data = [1.0, 0.0, 1.0, 1.0, 0.0, 1.0]
    assert st.bootstrap_ci(data) == st.bootstrap_ci(data)


def test_mcnemar_and_kappa():
    assert st.mcnemar([True] * 10, [False] * 10)["p_value"] < 0.01
    assert st.mcnemar([True, False], [True, False])["p_value"] is None
    assert st.cohens_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert st.cohens_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0
