import html
import json
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import override
from urllib.parse import parse_qs, urlparse

from topology_benchmark.application.catalog import BenchmarkCatalog
from topology_benchmark.application.errors import BenchmarkApplicationError
from topology_benchmark.core.errors import GenerationError
from topology_benchmark.core.problem.models import GenerationRequest


class DemoApplication:
    def __init__(
        self,
        catalog: BenchmarkCatalog,
        default_domain: str,
    ) -> None:
        catalog.require_domain(default_domain)
        self._catalog = catalog
        self.default_domain = default_domain

    @property
    def domains(self) -> tuple[str, ...]:
        return self._catalog.domains

    def problem_json(self, *, request: GenerationRequest, domain: str | None = None) -> bytes:
        selected = domain or self.default_domain
        problem = self._catalog.generate(
            domain=selected,
            request=request,
        )
        return json.dumps(asdict(problem), ensure_ascii=False).encode()

    def index_html(self) -> bytes:
        options = "".join(
            f'<option value="{html.escape(domain)}"'
            f"{' selected' if domain == self.default_domain else ''}>"
            f"{html.escape(domain)}</option>"
            for domain in self.domains
        )
        return _INDEX_HTML.replace("__DOMAIN_OPTIONS__", options).encode()


def serve_demo(
    *,
    catalog: BenchmarkCatalog,
    default_domain: str,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    application = DemoApplication(
        catalog,
        default_domain,
    )

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send(
                    HTTPStatus.OK,
                    "text/html; charset=utf-8",
                    application.index_html(),
                )
                return
            if parsed.path == "/health":
                self._send(HTTPStatus.OK, "application/json", b'{"status":"ok"}')
                return
            if parsed.path == "/api/problem":
                try:
                    query = parse_qs(parsed.query)
                    seed = int(query.get("seed", ["0"])[0])
                    difficulty = int(query.get("difficulty", ["5"])[0])
                    request = GenerationRequest(seed=seed, difficulty=difficulty)
                except (TypeError, ValueError) as error:
                    self._send_error(HTTPStatus.BAD_REQUEST, str(error))
                    return
                domain = query.get("domain", [application.default_domain])[0]
                try:
                    body = application.problem_json(
                        request=request,
                        domain=domain,
                    )
                except BenchmarkApplicationError as error:
                    self._send_error(HTTPStatus.BAD_REQUEST, str(error))
                    return
                except GenerationError as error:
                    self._send_error(HTTPStatus.SERVICE_UNAVAILABLE, str(error))
                    return
                except Exception as error:
                    self.log_error("problem generation failed: %s: %s", type(error).__name__, error)
                    self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")
                    return
                self._send(HTTPStatus.OK, "application/json; charset=utf-8", body)
                return
            self._send(HTTPStatus.NOT_FOUND, "application/json", b'{"error":"not found"}')

        def _send(self, status: HTTPStatus, media_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", media_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_error(self, status: HTTPStatus, message: str) -> None:
            self._send(
                status,
                "application/json; charset=utf-8",
                json.dumps({"error": message}).encode(),
            )

        @override
        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Topology Benchmark demo: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Topology Benchmark Demo</title>
  <style>
    :root { color-scheme: light; font: 16px/1.45 system-ui, sans-serif; }
    body { margin: 0; background: #f4f5f7; color: #17202a; }
    main { width: min(1100px, calc(100% - 32px)); margin: 24px auto 60px; }
    header, section { background: white; border: 1px solid #dfe3e8; border-radius: 12px;
      padding: 18px; margin-bottom: 16px; box-shadow: 0 2px 12px #17202a0d; }
    h1 { margin: 0 0 12px; font-size: 1.45rem; }
    h2 { margin: 0; font-size: 1.1rem; }
    .controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; }
    label { display: grid; gap: 4px; font-size: .82rem; color: #52606d; }
    input, select, button { font: inherit; padding: 8px 11px; border-radius: 7px;
      border: 1px solid #b8c2cc; background: white; }
    button { cursor: pointer; background: #174ea6; border-color: #174ea6; color: white; }
    button.secondary { background: white; color: #174ea6; }
    #status { margin-left: auto; color: #68737d; font-size: .9rem; }
    #question { font-size: 1.12rem; }
    #sections { display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
    .section { border: 1px solid #dfe3e8; border-radius: 9px; padding: 10px; overflow: auto; }
    .section img { display: block; width: 100%; height: auto; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; }
    .details { color: #68737d; font: .78rem ui-monospace, monospace; margin-top: 8px; }
    #answer { background: #f0f7ee; border-color: #a8c7a0; }
    [hidden] { display: none !important; }
  </style>
</head>
<body><main>
  <header>
    <h1>Topology Benchmark Demo</h1>
    <div class="controls">
      <label>Domain <select id="domain">__DOMAIN_OPTIONS__</select></label>
      <label>Seed <input id="seed" type="number" value="0"></label>
      <label>Difficulty <input id="difficulty" type="range" min="1" max="10" value="5">
        <span id="difficulty-value">5</span></label>
      <button id="regenerate">New random problem</button>
      <button id="replay" class="secondary">Replay seed</button>
      <span id="status"></span>
    </div>
  </header>
  <section><h2>Question</h2><p id="question">Loading…</p>
    <div id="problem-details" class="details"></div></section>
  <section><h2>Question material</h2><div id="sections"></div></section>
  <section><button id="reveal" class="secondary">Reveal ground truth</button>
    <pre id="answer" hidden></pre></section>
</main>
<script>
  const byId = id => document.getElementById(id);
  const objectUrls = [];
  function clearObjectUrls() { while (objectUrls.length) URL.revokeObjectURL(objectUrls.pop()); }
  function formatJson(value) { return JSON.stringify(value, null, 2); }
  function renderSection(section, index) {
    const card = document.createElement('article'); card.className = 'section';
    const title = document.createElement('strong');
    title.textContent = `Section ${index + 1} · ${section.media_type}`;
    card.append(title);
    if (section.media_type.startsWith('image/')) {
      const image = document.createElement('img'); image.alt = `Question section ${index + 1}`;
      if (section.content.startsWith('data:')) image.src = section.content;
      else if (section.media_type === 'image/svg+xml') {
        image.src = URL.createObjectURL(new Blob([section.content], {type: section.media_type}));
        objectUrls.push(image.src);
      } else image.src = `data:${section.media_type};base64,${section.content}`;
      card.append(image);
    } else if (section.media_type.startsWith('audio/')) {
      const audio = document.createElement('audio'); audio.controls = true;
      audio.src = section.content.startsWith('data:') ? section.content
        : `data:${section.media_type};base64,${section.content}`; card.append(audio);
    } else {
      const pre = document.createElement('pre');
      pre.textContent = section.content; card.append(pre);
    }
    return card;
  }
  async function load(randomize) {
    if (randomize) byId('seed').value = crypto.getRandomValues(new Uint32Array(1))[0];
    const domain = byId('domain').value;
    const seed = byId('seed').value, difficulty = byId('difficulty').value;
    byId('status').textContent = 'Generating…'; byId('answer').hidden = true; clearObjectUrls();
    try {
      const endpoint = `/api/problem?domain=${encodeURIComponent(domain)}`
        + `&seed=${encodeURIComponent(seed)}&difficulty=${difficulty}`;
      const response = await fetch(endpoint); const problem = await response.json();
      if (!response.ok) throw new Error(problem.error || response.statusText);
      byId('question').textContent = problem.question;
      byId('problem-details').textContent = formatJson(
        {seed: problem.seed, question_id: problem.question_id});
      byId('answer').textContent = formatJson(problem.answer);
      byId('sections').replaceChildren(...problem.sections.map(renderSection));
      history.replaceState(null, '', `/?domain=${encodeURIComponent(domain)}`
        + `&seed=${encodeURIComponent(seed)}&difficulty=${difficulty}`);
      byId('status').textContent = `${domain} · ${problem.question_id} · seed ${problem.seed}`;
    } catch (error) { byId('status').textContent = error.message; }
  }
  byId('difficulty').addEventListener('input', event => {
    byId('difficulty-value').textContent = event.target.value;
  });
  byId('domain').addEventListener('change', () => load(false));
  byId('regenerate').addEventListener('click', () => load(true));
  byId('replay').addEventListener('click', () => load(false));
  byId('reveal').addEventListener('click', () => byId('answer').hidden = !byId('answer').hidden);
  const initial = new URLSearchParams(location.search);
  if (initial.has('domain')) byId('domain').value = initial.get('domain');
  if (initial.has('seed')) byId('seed').value = initial.get('seed');
  if (initial.has('difficulty')) byId('difficulty').value = initial.get('difficulty');
  byId('difficulty-value').textContent = byId('difficulty').value; load(false);
</script></body></html>"""
