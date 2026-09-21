from copy import deepcopy
import pytest
from mle_benchmark.scoring import grade, seal_snapshot, aggregate


def fixtures(direction="higher"):
    s = seal_snapshot({"competition_id":"demo", "metric":"accuracy", "direction":direction,
        "test_set_id":"official-v1", "split":"private", "track":"official", "unit":"team",
        "source_url":"https://example.test/fixture", "frozen_at":"2026-09-15T00:00:00Z",
        "frozen":True, "complete":True, "final":True, "score_decimals":5,
        "rows":[{"id":str(i),"score":v} for i,v in enumerate([.1,.2,.2,.4])]})
    r={k:s[k] for k in ("competition_id","metric","direction","test_set_id","split","track")}
    r["raw_score"]=.2
    return s,r


def test_ties_half_credit_and_direction():
    s,r=fixtures(); x=grade(s,r)
    assert (x.beaten,x.tied,x.percentile,x.quadratic_score)==(1,2,.5,25)
    s,r=fixtures("lower"); assert grade(s,r).quadratic_score==25


def test_extremes_and_monotonicity():
    for direction in ("higher","lower"):
        s,r=fixtures(direction)
        values=[grade(s,{**r,"raw_score":v}).quadratic_score for v in [0,.15,.2,.3,.5]]
        assert values==sorted(values,reverse=direction=="lower")
        assert sorted([values[0],values[-1]])==[0,100]


@pytest.mark.parametrize("field,value",[("split","public"),("test_set_id","new-holdout"),("metric","rmse"),("track","offline")])
def test_no_cross_distribution_rank(field,value):
    s,r=fixtures(); r[field]=value
    with pytest.raises(ValueError): grade(s,r)


@pytest.mark.parametrize("value",["NaN","Infinity","-Infinity","nonsense"])
def test_invalid_scores(value):
    s,r=fixtures(); r["raw_score"]=value
    with pytest.raises(ValueError): grade(s,r)


def test_snapshot_tampering_and_duplicate_team():
    s,r=fixtures(); s["rows"][0]["score"]=.9
    with pytest.raises(ValueError,match="checksum"): grade(s,r)
    s,r=fixtures(); s["rows"][0]["id"]="1"; s=seal_snapshot(s)
    with pytest.raises(ValueError,match="unique"): grade(s,r)


def test_precision_ties():
    s,r=fixtures(); r["raw_score"]=.2000001
    assert grade(s,r).tied==2


def test_topn_or_rolling_snapshot_rejected():
    for field in ("final","complete","frozen"):
        s,r=fixtures(); s[field]=False; s=seal_snapshot(s)
        with pytest.raises(ValueError): grade(s,r)


def test_offline_cannot_use_human_teams():
    s,r=fixtures(); s["track"]=r["track"]="offline"; s=seal_snapshot(s)
    with pytest.raises(ValueError,match="reference systems"): grade(s,r)


def tasks():
    return [{"id":t,"tier":t,"track":"official","test_set_id":"original-v1","snapshot_sha256":"frozen-hash"} for t in ("easy","medium","hard")]


def bind(rows):
    return [{"track":"official","test_set_id":"original-v1","snapshot_sha256":"frozen-hash",**r} for r in rows]


def test_missing_runs_and_failed_runs_not_dropped():
    rows=[{"task_id":"easy","seed":17,"status":"ok","score":100},
          {"task_id":"medium","seed":17,"status":"agent_failure"}]
    out=aggregate(tasks(),bind(rows),[17],bootstrap_samples=100)
    assert out["overall"]==pytest.approx(100/3)
    assert out["missing_runs"]==1


def test_no_best_seed_selection_and_reproducible_ci():
    rows=[{"task_id":t["id"],"seed":seed,"status":"ok","score":100 if seed==17 else 0}
          for t in tasks() for seed in (17,42)]
    rows=bind(rows)
    a=aggregate(tasks(),rows,[17,42],bootstrap_samples=100)
    assert a["overall"]==50
    assert a==aggregate(tasks(),rows,[17,42],bootstrap_samples=100)


def test_infra_not_agent_failure():
    out=aggregate(tasks(),bind([{"task_id":"easy","seed":17,"status":"infra_failure"}]),[17],bootstrap_samples=100)
    assert out["overall"] is None


def test_mixed_tracks_rejected():
    t=tasks(); t[0]["track"]="offline"
    with pytest.raises(ValueError): aggregate(t,[],[17],bootstrap_samples=100)


@pytest.mark.parametrize("field,value",[("track","offline"),("test_set_id","wrong-test"),("snapshot_sha256","wrong-hash")])
def test_result_provenance_cannot_cross_manifest(field,value):
    rows=bind([{"task_id":"easy","seed":17,"status":"ok","score":100}]); rows[0][field]=value
    with pytest.raises(ValueError,match="provenance"): aggregate(tasks(),rows,[17],bootstrap_samples=100)
