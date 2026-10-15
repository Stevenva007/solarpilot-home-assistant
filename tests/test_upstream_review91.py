"""Public source-review gate fixtures never contact GitHub or runtime devices."""
from copy import deepcopy
from datetime import datetime, timezone
from http.client import IncompleteRead
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location("upstream_review91", ROOT / "tools" / "check_upstream_review.py")
gate = module_from_spec(spec); spec.loader.exec_module(gate)
NOW = datetime(2026, 10, 15, 16, tzinfo=timezone.utc)
SECRET = "synthetic_secret_never_print_this"


def checkpoint():
    return {"schema":1, "reviewed_at":"2026-10-15T12:00:00Z",
        "assessment":{"status":"complete_no_unprocessed_changes", "summary":"Synthetic review of both public upstream source contracts.",
                      "compatibility_claim":False, "evidence_document":"docs/UPSTREAM_BRONNEN.md"},
        "repositories":[{"repository":repo, "default_branch":"main", "head_commit":char*40,
            "latest_release":{"tag":"v1.2.3", "commit":char*40, "target_commitish":"main",
                              "published_at":"2026-10-14T12:00:00Z", "selection":"github_latest_published_stable"},
            "reviewed_base_commit":char*40, "review_result":"no_additional_changes"}
            for repo,char in zip(gate.REPOSITORIES,"ab")]}


def upstream(data=None):
    result = {}
    for row in (data or checkpoint())["repositories"]:
        repo = row["repository"]; release = row["latest_release"]
        result[repo,""] = {"full_name":repo,"private":False,"default_branch":row["default_branch"]}
        result[repo,"branches/"+row["default_branch"]] = {"name":row["default_branch"],"commit":{"sha":row["head_commit"]}}
        result[repo,"releases/latest"] = {"draft":False,"prerelease":False,"tag_name":release["tag"],
            "target_commitish":release["target_commitish"],"published_at":release["published_at"]}
        result[repo,"git/ref/tags/"+release["tag"]] = {"ref":"refs/tags/"+release["tag"],
            "object":{"type":"commit","sha":release["commit"]}}
    return result


def reader(table, calls=None):
    def fetch(repo,suffix):
        if calls is not None: calls.append((repo,suffix))
        return deepcopy(table[repo,suffix])
    return fetch


def test_reviewed_current_sources_pass_without_mutation_or_compatibility_claim():
    data=checkpoint(); before=deepcopy(data); calls=[]
    assert gate.validate_checkpoint(data, NOW) is data
    assert gate.check_online(data, reader(upstream(data),calls)) is True
    assert data == before
    assert len(calls) == 8 and not any("pull" in suffix for _,suffix in calls)
    assert data["assessment"]["compatibility_claim"] is False


@pytest.mark.parametrize("path,bad", [
    (("schema",),True), (("schema",),2), (("reviewed_at",),"2026-10-15T12:00:00"),
    (("reviewed_at",),"2099-01-01T00:00:00Z"), (("assessment","status"),"pending"),
    (("assessment","compatibility_claim"),True), (("assessment","summary"),""),
    (("assessment","evidence_document"),"somewhere_private.md"),
    (("repositories",0,"head_commit"),"a"*7), (("repositories",0,"head_commit"),True),
    (("repositories",0,"repository"),"unreviewed/other"),
    (("repositories",0,"default_branch"),"../../main"),
    (("repositories",0,"reviewed_base_commit"),"c"*40),
    (("repositories",0,"review_result"),"unprocessed"),
    (("repositories",0,"latest_release","selection"),"open_pull_request"),
    (("repositories",0,"latest_release","published_at"),"2026-10-16T00:00:00Z"),
])
def test_unreviewed_or_malformed_checkpoint_is_rejected(path,bad):
    data=checkpoint(); parent=data
    for key in path[:-1]: parent=parent[key]
    parent[path[-1]]=bad
    with pytest.raises(gate.ReviewError): gate.validate_checkpoint(data,NOW)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra", "unknown_field"])
def test_both_exact_repositories_and_closed_schema_are_required(mutation):
    data=checkpoint()
    if mutation=="missing": data["repositories"].pop()
    elif mutation=="duplicate": data["repositories"][1]=deepcopy(data["repositories"][0])
    elif mutation=="extra": data["repositories"].append(deepcopy(data["repositories"][0]))
    else: data["unreviewed_exception"]=True
    with pytest.raises(gate.ReviewError): gate.validate_checkpoint(data,NOW)


@pytest.mark.parametrize("mutation", ["head", "default_branch", "release_tag", "moved_same_tag", "target_commitish", "publication"])
def test_changed_upstream_is_blocked_when_version_or_head_alone_matches(mutation):
    data=checkpoint(); table=upstream(data); repo=gate.REPOSITORIES[0]
    if mutation=="head": table[repo,"branches/main"]["commit"]["sha"]="c"*40
    elif mutation=="default_branch":
        table[repo,""]["default_branch"]="stable"
        table[repo,"branches/stable"]={"name":"stable","commit":{"sha":"a"*40}}
    elif mutation=="release_tag":
        table[repo,"releases/latest"]["tag_name"]="v1.2.4"
        table[repo,"git/ref/tags/v1.2.4"]={"ref":"refs/tags/v1.2.4","object":{"type":"commit","sha":"a"*40}}
    elif mutation=="moved_same_tag": table[repo,"git/ref/tags/v1.2.3"]["object"]["sha"]="c"*40
    elif mutation=="target_commitish": table[repo,"releases/latest"]["target_commitish"]="stable"
    else: table[repo,"releases/latest"]["published_at"]="2026-10-14T13:00:00Z"
    before=deepcopy(data)
    with pytest.raises(gate.ReviewError,match="unreviewed upstream change"): gate.check_online(data,reader(table))
    assert data == before


def test_annotated_release_tag_is_peeled_to_commit_not_target_commitish():
    data=checkpoint(); table=upstream(data); repo=gate.REPOSITORIES[0]
    table[repo,"git/ref/tags/v1.2.3"]["object"]={"type":"tag","sha":"c"*40}
    table[repo,"git/tags/"+"c"*40]={"sha":"c"*40,"object":{"type":"tag","sha":"d"*40}}
    table[repo,"git/tags/"+"d"*40]={"sha":"d"*40,"object":{"type":"commit","sha":"a"*40}}
    assert gate.check_online(data,reader(table))


@pytest.mark.parametrize("mutation", ["cycle", "tree", "bad_sha", "wrong_ref", "wrong_annotation", "too_deep"])
def test_invalid_release_tag_never_falls_back_to_branch_head(mutation):
    table=upstream(); repo=gate.REPOSITORIES[0]; ref=table[repo,"git/ref/tags/v1.2.3"]
    if mutation=="cycle":
        ref["object"]={"type":"tag","sha":"c"*40}
        table[repo,"git/tags/"+"c"*40]={"sha":"c"*40,"object":{"type":"tag","sha":"c"*40}}
    elif mutation=="tree": ref["object"]["type"]="tree"
    elif mutation=="bad_sha": ref["object"]["sha"]=True
    elif mutation=="wrong_ref": ref["ref"]="refs/heads/v1.2.3"
    elif mutation=="wrong_annotation":
        ref["object"]={"type":"tag","sha":"c"*40}
        table[repo,"git/tags/"+"c"*40]={"sha":"d"*40,"object":{"type":"commit","sha":"a"*40}}
    else:
        ref["object"]={"type":"tag","sha":"0"*40}
        for index in range(6):
            table[repo,"git/tags/"+str(index)*40]={"sha":str(index)*40,"object":{"type":"tag","sha":str(index+1)*40}}
    with pytest.raises(gate.ReviewError): gate.check_online(checkpoint(),reader(table))


@pytest.mark.parametrize("suffix,key,bad", [
    ("","full_name","unreviewed/other"), ("","private",True), ("","default_branch",None),
    ("branches/main","name","other"), ("branches/main","commit",None),
    ("releases/latest","draft",True), ("releases/latest","prerelease",True),
    ("releases/latest","published_at",None), ("releases/latest","tag_name","../bad"),
])
def test_missing_or_unpublished_source_is_not_reviewed_release(suffix,key,bad):
    table=upstream(); table[gate.REPOSITORIES[0],suffix][key]=bad
    with pytest.raises(gate.ReviewError): gate.check_online(checkpoint(),reader(table))


class Response:
    def __init__(self,payload): self.payload=payload; self.requested=[]
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,size): self.requested.append(size); return self.payload[:size]


class Opener:
    def __init__(self,response=None,error=None): self.response=response; self.error=error; self.calls=[]
    def open(self,request,timeout):
        self.calls.append((request,timeout))
        if self.error is not None: raise self.error
        return self.response


def test_reader_bounds_timeout_response_and_optional_token_header():
    client=gate.GitHubReader(SECRET); response=Response(b'{"ok":true}'); opener=Opener(response)
    client._opener=opener
    assert client(gate.REPOSITORIES[0],"") == {"ok":True}
    request,timeout=opener.calls[0]
    assert request.full_url == "https://api.github.com/repos/"+gate.REPOSITORIES[0]
    assert 0 < timeout <= gate.REQUEST_TIMEOUT_S
    assert request.get_header("Authorization") == "Bearer "+SECRET and SECRET not in request.full_url
    assert response.requested == [gate.MAX_RESPONSE_BYTES+1]
    plain=gate.GitHubReader(); plain._opener=Opener(Response(b'{}')); plain(gate.REPOSITORIES[0],"")
    assert plain._opener.calls[0][0].get_header("Authorization") is None


@pytest.mark.parametrize("payload", [b'\xff',b'{"broken":',b'[]',b'x'*(gate.MAX_RESPONSE_BYTES+1)])
def test_reader_rejects_invalid_truncated_nonobject_or_oversized_json(payload):
    client=gate.GitHubReader(); client._opener=Opener(Response(payload))
    with pytest.raises(gate.ReviewError): client(gate.REPOSITORIES[0],"")


@pytest.mark.parametrize("error", [URLError(SECRET),TimeoutError(SECRET),OSError(SECRET),IncompleteRead(SECRET.encode()),
    *[HTTPError("https://api.github.com/",code,SECRET,{},None) for code in (403,404,429,500)]])
def test_network_failure_is_nonzero_and_never_exposes_body_or_token(error,tmp_path,monkeypatch,capsys):
    path=tmp_path/"review.json"; path.write_text(json.dumps(checkpoint()))
    client=gate.GitHubReader(SECRET); client._opener=Opener(error=error)
    monkeypatch.setattr(gate,"GitHubReader",lambda token:client)
    monkeypatch.setenv("GITHUB_TOKEN",SECRET)
    assert gate.main(["--checkpoint",str(path)]) == 1
    output=capsys.readouterr()
    assert "Upstream review FAILED" in output.err
    assert SECRET not in output.err+output.out
    assert not output.out


def test_redirect_is_refused_before_auth_can_be_forwarded():
    request=Request("https://api.github.com/repos/test/repo",headers={"Authorization":"Bearer "+SECRET})
    with pytest.raises(gate.ReviewError,match="redirected"):
        gate.NoRedirect().redirect_request(request,None,302,"found",{},"https://untrusted.invalid/")


def test_total_timeout_starts_no_additional_network_request():
    client=gate.GitHubReader(); client._deadline=-1; client._opener=Opener(Response(b'{}'))
    with pytest.raises(gate.ReviewError,match="total timeout"): client(gate.REPOSITORIES[0],"")
    assert not client._opener.calls


@pytest.mark.parametrize("bad", [SECRET+"\n",SECRET+" ",SECRET+"\u0100"])
def test_invalid_token_is_rejected_without_exposure(bad):
    with pytest.raises(gate.ReviewError) as error: gate.GitHubReader(bad)
    assert SECRET not in str(error.value)


def test_cli_online_default_and_offline_explicitly_disclaims_freshness(tmp_path,monkeypatch,capsys):
    data=checkpoint(); path=tmp_path/"review.json"; path.write_text(json.dumps(data)); before=path.read_bytes(); calls=[]
    monkeypatch.setattr(gate,"GitHubReader",lambda token:reader(upstream(data),calls))
    assert gate.main(["--checkpoint",str(path)]) == 0
    assert len(calls) == 8 and "Source freshness only" in capsys.readouterr().out
    calls.clear()
    assert gate.main(["--checkpoint",str(path),"--offline"]) == 0
    assert not calls and "freshness_not_checked" in capsys.readouterr().out
    assert path.read_bytes() == before


def test_committed_checkpoint_schema_has_both_public_repositories():
    data=json.loads((ROOT/"docs"/"upstream_review.json").read_text())
    assert gate.validate_checkpoint(data) is data
