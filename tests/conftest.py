"""A miniature app laid out like Dog Cafe, in a temporary folder, for the tests to read."""

import subprocess
import textwrap
from pathlib import Path

import pytest

FILES = {
    ".config/ianf-product-map.toml": """
        version = 1
        name = "Tiny Cafe"
        adapter = "dog-cafe"
        source = "app"
        static = "static"
        out = "docs/product-map"
    """,
    ".config/ianf-tracker.toml": """
        version = 1
        kind = "jira"
        site = "tiny.atlassian.net"
        space = "TINY"
    """,
    "app/config/routerRegisterFromAttributes.php": """
        <?php
        use App\\Http\\Controllers\\PageController;
        return [PageController::class];
    """,
    "app/src/Http/Controllers/PageController.php": """
        <?php
        namespace App\\Http\\Controllers;
        use App\\Http\\FormRequests\\NoteRequest;
        final readonly class PageController extends Controller
        {
            protected const string NOTE_ROUTE = '/note';

            #[Get('/')]
            /**
             * Render the home page.
             */
            public function home(ViewRenderer $viewRenderer): Response
            {
                return $viewRenderer->render(status: 200, page: 'home');
            }

            #[Get(self::NOTE_ROUTE)]
            public function noteGet(ViewRenderer $viewRenderer, Auth $auth): Response
            {
                return $this->renderNote($viewRenderer, $auth);
            }

            #[Post(self::NOTE_ROUTE)]
            /**
             * Save a note. On failure, show the form again.
             * @return Response
             */
            public function notePost(NoteRequest $request): Response
            {
                return Response::redirect(303, '/');
            }

            #[Get('/api/v1/search')]
            public function search(): Response
            {
                return Response::json(200, []);
            }

            private function renderNote(ViewRenderer $viewRenderer, Auth $auth): Response
            {
                $auth->guard(true);
                if ($x === '}') { return $viewRenderer->error(403); }
                return $viewRenderer->render(status: 200, page: 'note');
            }
        }
    """,
    "app/src/Http/FormRequests/NoteRequest.php": """
        <?php
        final readonly class NoteRequest extends FormRequest
        {
            protected const array EXPECTED_INPUTS = [
                'note' => [
                    'filter' => ['type' => FILTER_UNSAFE_RAW],
                    'rules' => ['required', 'max:200'],
                ],
                'stars' => [
                    'filter' => ['type' => FILTER_VALIDATE_INT],
                    'rules' => ['max:5'],
                ],
            ];
        }
    """,
    "app/src/Framework/Validation/RuleFactory.php": """
        <?php
        use App\\Framework\\Validation\\Rules\\RequiredRule;
        use App\\Framework\\Validation\\Rules\\MaxStringRule;
        use App\\Framework\\Validation\\Rules\\MaxIntRule;
        final class RuleFactory
        {
            public static function fromString(string $rule, string $type): RuleInterface
            {
                switch ($name) {
                    case 'required': return new RequiredRule();
                    case 'max':
                        return match ($type) {
                            'string' => new MaxStringRule((int) $parameter),
                            'int'    => new MaxIntRule((int) $parameter),
                        };
                }
            }
        }
    """,
    "app/src/Framework/Validation/Rules/RequiredRule.php": "<?php new Error(ErrorCode::Missing);",
    "app/src/Framework/Validation/Rules/MaxStringRule.php": "<?php new Error(ErrorCode::TooLong);",
    "app/src/Framework/Validation/Rules/MaxIntRule.php": "<?php new Error(ErrorCode::TooLarge);",
    "app/src/Framework/Errors/ErrorCode.php": """
        <?php
        enum ErrorCode: int
        {
            public function message(): string
            {
                return match ($this) {
                    self::Missing => '`:field` is required',
                    self::TooLong => '`:field` can\\'t be longer than :parameter',
                    self::TooLarge => '`:field` can\\'t be larger than :parameter',
                };
            }
        }
    """,
    "app/src/Enums/DrinkSize.php": """
        <?php
        enum DrinkSize: int
        {
            case Small = 1;
            case ExtraLarge = 2;
        }
    """,
    "app/resources/views/layouts/main.php": """
        <?php
        $bar = $p['in'] ? '<a href="/account">Account</a>' : '<a href="/login">Login</a>';
        ?>
        <nav><a href="/">Home</a><input type="text" placeholder="Search drinks" /><?= $bar ?></nav>
        {{body}}
    """,
    "app/resources/views/pages/home/head.php": """
        <title>Tiny Cafe</title>
        <script src="/js/main.js"></script>
        <script src="/js/search.js"></script>
    """,
    "app/resources/views/pages/home/body.php": """
        <?php $e = fn ($v) => $v; ?>
        <h1>Welcome &amp; hello</h1>
        <p>Today's specials</p>
        <?= '<a href="/menu/' . $e($p['slug']) . '">See the menu</a>' ?>
        <script>var hidden = "not shown";</script>
    """,
    "app/resources/views/pages/note/head.php": """
        <title><?= $e($p['name']) ?> - Tiny Cafe</title>
        <script src="/js/main.js"></script>
    """,
    "app/resources/views/pages/note/body.php": """
        <form>
            <input type="hidden" name="token" value="x"/>
            <label for="sugar">Sugar</label><input type="checkbox" id="sugar" name="s"/>
            <label><input type="radio" name="milk"/>Oat milk</label>
            <textarea name="note"></textarea>
            <select name="cup"></select>
            <button>Save ✓</button>
            <input type="submit" value="Send"/>
        </form>
    """,
    "app/resources/views/pages/thanks/body.php": "<p>Thanks!</p>",
    "static/js/main.js": "if (!confirm('Leave this page?')) { return; }",
    "static/js/search.js": """
        results.innerHTML = '<div id="s">Searching...</div>';
        results.textContent = "No results";
        list.innerHTML = `<b>${count}</b>`;
    """,
}


def write(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip("\n"))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """The miniature app, in a git repository with one commit tagged v1.2.0."""
    root = tmp_path / "tiny-cafe"
    write(root, FILES)
    git = ["git", "-C", str(root), "-c", "user.name=T", "-c", "user.email=t@example.com"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run(
        [*git, "commit", "-qm", "Start", "--date=2026-10-01T09:00:00"],
        check=True,
        env={"GIT_COMMITTER_DATE": "2026-10-01T09:00:00", "PATH": "/usr/bin:/bin"},
    )
    subprocess.run([*git, "tag", "v1.2.0"], check=True)
    return root


@pytest.fixture
def maps(tmp_path: Path) -> Path:
    """A folder of installed maps, such as ~/.claude/product-maps, not yet created."""
    return tmp_path / "product-maps"
