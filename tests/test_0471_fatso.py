from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def text(rel): return (ROOT/rel).read_text(encoding='utf-8')

def test_fatso_release_identity_and_foundations():
    assert json.loads(text('web/package.json'))['version']=='0.52.0'
    assert 'APP_VERSION = "0.52.0"' in text('api/app/config.py')
    assert '0.52.0 — Lazy Lizard' in text('README.md')
    assert (ROOT/'web/src/components/ui/UiButton.vue').exists()
    assert (ROOT/'web/src/components/ui/UiCard.vue').exists()
    assert (ROOT/'web/src/components/ui/UiField.vue').exists()
    assert (ROOT/'web/src/components/ui/UiStatusBadge.vue').exists()
    assert not (ROOT/'web/src/components/ActionButton.vue').exists()

def test_active_shell_has_no_release_era_v030_names():
    active='\n'.join([text('web/src/App.vue'),text('web/src/runtime/runtime.js'),text('web/src/style.css')])
    assert 'v030' not in active
    assert 'runtimeView' in text('web/src/App.vue')

def test_accessibility_foundations_and_storybook_taxonomy():
    style=text('web/src/style.css')
    assert '--focus-ring:' in style
    assert ':focus-visible' in style
    assert 'prefers-reduced-motion' in style
    assert 'prefers-contrast: more' in style
    assert 'Foundations/Actions/Button' in text('web/src/components/ui/UiButton.stories.ts')
    assert 'Foundations/Feedback/Status Badge' in text('web/src/components/ui/UiStatusBadge.stories.ts')
    assert (ROOT/'web/src/components/RolePermissionMatrix.stories.ts').exists()
