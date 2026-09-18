from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM_STORE = (ROOT / "api/app/system_store.py").read_text(encoding="utf-8")
MAIN = (ROOT / "api/app/main.py").read_text(encoding="utf-8")
JOBS = (ROOT / "api/app/jobs.py").read_text(encoding="utf-8")
I18N_TRANSLATION = (ROOT / "api/app/i18n_translation.py").read_text(encoding="utf-8")
VIEW = (ROOT / "web/src/views/ResearchView.vue").read_text(encoding="utf-8")
SETTINGS = (ROOT / "web/src/components/research/ResearchSettingsDrawer.vue").read_text(encoding="utf-8")
PIPELINE = (ROOT / "web/src/components/research/ResearchPipelineBar.vue").read_text(encoding="utf-8")
STYLE = (ROOT / "web/src/style.css").read_text(encoding="utf-8")


def _translation_dicts() -> dict[str, dict[str, str]]:
    tree = ast.parse(SYSTEM_STORE)
    found: dict[str, dict[str, str]] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in {"DEFAULT_EN_US", "DEFAULT_FR_CA"}:
                found[node.target.id] = ast.literal_eval(node.value)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if (
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "update"
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id in {"DEFAULT_EN_US", "DEFAULT_FR_CA"}
                and len(call.args) == 1
            ):
                found.setdefault(call.func.value.id, {}).update(ast.literal_eval(call.args[0]))
    return found


def test_0350_release_version_is_consistent():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.44.0"
    assert 'version="0.44.0"' in MAIN
    assert "Corpus Viewer 0.44.0" in (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "DerridAI 0.44.0" in (ROOT / "web/src/App.vue").read_text(encoding="utf-8")
    assert "## 0.35.10" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_research_supports_multiple_simultaneous_jobs_without_a_ui_job_cap():
    assert "ResearchPipelineBar" in VIEW
    assert "sessionJobIds" in VIEW
    assert "Promise.all(" in VIEW and "activeSessionJobs.map" in VIEW
    assert "sessionJobIds.value.add(job.id)" in VIEW
    assert "starting.value" in VIEW
    # The page may serialize the submission request itself, but an existing active
    # job must not disable starting a second pipeline.
    assert "activeJob.value &&" not in VIEW
    assert "jobs.length >=" not in VIEW
    assert "Active research pipelines" in PIPELINE
    assert "overflow-x:auto" in STYLE
    assert "threading.Thread" in JOBS and "daemon=True" in JOBS


def test_parallel_research_keeps_existing_role_boundaries():
    assert 'auth.can("rag.run")' in VIEW
    assert 'auth.can("rag.jobs.own")' in VIEW
    assert "auth.can('evidence.select')" in VIEW
    assert "canManageRuns" in VIEW
    assert "rag.jobs.own" in MAIN and "rag.run" in MAIN


def test_expert_settings_is_a_centered_sectioned_settings_studio():
    assert "research-settings-studio-dialog" in SETTINGS
    assert "research-settings-studio-body" in SETTINGS
    assert '"retrieval"' in SETTINGS
    assert '"evidence"' in SETTINGS
    assert '"generation"' in SETTINGS
    assert "research-settings-nav" in SETTINGS
    assert "research-settings-card-grid" in SETTINGS
    assert "width:min(1080px" in STYLE
    assert "grid-template-columns:230px minmax(0,1fr)" in STYLE
    # Do not regress to illegibly tiny helper typography.
    assert "research-settings-card>p{margin:0 0 13px;color:#66758a;font-size:12.5px" in STYLE
    assert "research-settings-nav>button b{font-size:13px" in STYLE


def test_research_pipeline_and_settings_have_storybook_coverage():
    assert (ROOT / "web/src/components/research/ResearchPipelineBar.stories.ts").exists()
    story = (ROOT / "web/src/components/research/ResearchPipelineBar.stories.ts").read_text(encoding="utf-8")
    assert story.count("status:") >= 3
    assert (ROOT / "web/src/components/research/ResearchSettingsDrawer.stories.ts").exists()


def test_english_and_quebec_french_dictionaries_are_complete_and_placeholder_safe():
    dictionaries = _translation_dicts()
    english = dictionaries["DEFAULT_EN_US"]
    french = dictionaries["DEFAULT_FR_CA"]
    assert len(english) >= 1500
    assert set(english) == set(french)
    assert french["language.french_ca"] == "Français"
    assert "500" in french["vector.sync_behavior_help"]
    assert re.findall(r"\d+", english["vector.sync_behavior_help"]) == re.findall(r"\d+", french["vector.sync_behavior_help"])
    for key, source in english.items():
        source_slots = sorted(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", source))
        target_slots = sorted(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", french[key]))
        assert source_slots == target_slots, key


def test_all_literal_i18n_keys_used_by_web_code_exist_in_both_builtins():
    dictionaries = _translation_dicts()
    english = dictionaries["DEFAULT_EN_US"]
    french = dictionaries["DEFAULT_FR_CA"]
    used: set[str] = set()
    patterns = [
        re.compile(r"\bi18n\.(?:t|tf)\(\s*['\"]([^'\"]+)['\"]"),
        re.compile(r"\btrf?\(\s*['\"]([^'\"]+)['\"]"),
    ]
    for path in (ROOT / "web/src").rglob("*"):
        if path.suffix not in {".vue", ".ts", ".js"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            used.update(pattern.findall(text))
    assert used - set(english) == set()
    assert used - set(french) == set()


def test_fr_ca_translation_prompt_explicitly_targets_quebec_and_oqlf():
    assert "professional Canadian French as written in Québec" in I18N_TRANSLATION
    assert "Office québécois de la langue française (OQLF)" in I18N_TRANSLATION
    assert "avoid France-only wording" in I18N_TRANSLATION
    assert "Canadian French typography" in I18N_TRANSLATION


def test_builtin_dictionaries_bootstrap_current_values_and_preserve_admin_edits(tmp_path, monkeypatch):
    import app.system_store as store_module
    from app.persistence import SQLiteSystemRepository

    repository = SQLiteSystemRepository(tmp_path / "derridai-system.sqlite3")
    monkeypatch.setattr(store_module, "system_repository", repository)

    store = store_module.SystemStore()
    fresh = store.snapshot()
    assert fresh["languages"]["fr-CA"]["name"] == "Français"
    assert fresh["languages"]["en-US"]["dictionary"]["app.name"] == "DerridAI"
    assert fresh["languages"]["fr-CA"]["dictionary"]["nav.rag"] == "Recherche"

    fr = store.get_language("fr-CA")
    dictionary = dict(fr["dictionary"])
    dictionary["app.subtitle"] = "Mon libellé personnalisé"
    store.put_language("fr-CA", name=fr["name"], flag=fr["flag"], dictionary=dictionary)

    preserved = store_module.SystemStore().snapshot()
    assert preserved["languages"]["fr-CA"]["dictionary"]["app.subtitle"] == "Mon libellé personnalisé"


def test_quebec_localization_policy_is_documented():
    policy = (ROOT / "docs/LOCALIZATION_FR_CA.md").read_text(encoding="utf-8")
    assert "professional Canadian French as written in Québec" in policy
    assert "OQLF" in policy
    assert "Never translate corpus passages" in policy
    assert "language_dictionary_revision" not in policy or "0.35.0" in policy
