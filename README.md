
<body>

<h1>LocalMind – Local-First AI Desktop Search</h1>

<p><strong>LocalMind</strong> is a private, offline intelligence layer that sits on top of your personal file system. It continuously indexes documents, images and code into a <strong>vector knowledge base</strong> and lets you search by <strong>semantic meaning</strong> instead of keywords – <em>nothing ever leaves your machine</em>.</p>

<h2>✨ Key Features</h2>
<ul>
  <li>100 % offline – no cloud, no external APIs</li>
  <li>Semantic search – find ideas, not just words</li>
  <li>Incremental indexing – only new or changed files are re-processed</li>
  <li>Cross-platform – Windows, macOS, Linux</li>
  <li>Tiny footprint – single ~15 MB executable + a few Docker images for dev</li>
</ul>

<h2>🏗️ Architecture (dev mode)</h2>
<div class="box">
<pre>
┌-----------------------------┐
│  React + Vite (TypeScript) │  ←-- http://localhost:5173
└------------┬----------------┘
             │  REST
┌------------┴----------------┐
│  Go orchestrator (Gin)      │  ←-- http://localhost:8080
│  - REST API                 │
│  - job queue (Asynq)        │
└------------┬----------------┘
             │  gRPC
┌------------┴----------------┐
│  Python AI service          │  ←-- localhost:50051
│  - embeddings               │
│  - vector search            │
└------------┬----------------┘
             │  SQL / pgvector
┌------------┴----------------┐
│  PostgreSQL (+pgvector)     │
│  Redis (task queue)         │
└-----------------------------┘
</pre>
</div>
<p>Production build packages <strong>Go binary + Python service + embedded DB</strong> into a single installer.</p>

<h2>🚀 Quick Start (Windows / macOS / Linux)</h2>
<p>Prerequisites: <a href="https://www.docker.com/products/docker-desktop/" target="_blank">Docker Desktop</a></p>
<ol>
  <li>Clone / unzip this repo</li>
  <li>Open a terminal in the root folder</li>
  <li>Spin everything up:
    <pre><code>docker compose up --build</code></pre>
  </li>
  <li>Browse:
    <ul>
      <li>UI → <a href="http://localhost:5173" target="_blank">http://localhost:5173</a></li>
      <li>Health check → <a href="http://localhost:8080/ping" target="_blank">http://localhost:8080/ping</a></li>
      <li>gRPC reflection → <code>localhost:50051</code></li>
    </ul>
  </li>
</ol>

<h2>🔧 Development</h2>
<table>
  <thead><tr><th>Task</th><th>Command</th></tr></thead>
  <tbody>
    <tr><td>Frontend live reload</td><td><code>cd frontend &amp;&amp; npm install &amp;&amp; npm run dev</code></td></tr>
    <tr><td>Go tests</td><td><code>cd orchestrator &amp;&amp; go test ./...</code></td></tr>
    <tr><td>Python tests</td><td><code>cd ai-engine &amp;&amp; python -m pytest</code></td></tr>
    <tr><td>Build Windows exe</td><td><code>cd orchestrator &amp;&amp; .\scripts\build.ps1</code></td></tr>
    <tr><td>Build macOS / Linux bin</td><td><code>cd orchestrator &amp;&amp; ./scripts/build.sh</code></td></tr>
  </tbody>
</table>

<h2>📦 Packaging</h2>
<p>Ready-made installers are produced in <code>installer/</code>:</p>
<ul>
  <li><strong>Windows</strong> – WiX tool-set → <code>localmind-x64.msi</code></li>
  <li><strong>macOS</strong> – <code>create-dmg</code> → <code>LocalMind.dmg</code></li>
  <li><strong>Linux</strong> – <code>dpkg-deb</code> → <code>localmind_amd64.deb</code></li>
</ul>
<p>Build script (CI or local):</p>
<div class="box">
  <code>.\scripts\release.ps1</code> (Windows) or <code>./scripts/release.sh</code> (Unix)
</div>

<h2>🧪 API Examples</h2>
<p><strong>REST (Go orchestrator)</strong></p>
<pre><code>GET  /api/search?q=holiday photos&amp;top=10
POST /api/index { "path": "C:\Users\me\Docs" }</code></pre>
<p><strong>gRPC (Python AI)</strong> – see <code>ai-engine/proto/ai.proto</code></p>
<pre><code>from ai_pb2 import EmbedRequest
stub.Embed(EmbedRequest(text="sunset on the beach"))</code></pre>

<h2>🔒 Privacy &amp; Security</h2>
<ul>
  <li>Every byte stays on your disk.</li>
  <li>No telemetry, no phoning home.</li>
  <li>File-system access <strong>read-only</strong> (never modifies your data).</li>
  <li>gRPC/REST bound to <strong>localhost only</strong> in production builds.</li>
</ul>

<h2>🛠️ Tech Stack</h2>
<table>
  <thead><tr><th>Layer</th><th>Tech</th></tr></thead>
  <tbody>
    <tr><td>Frontend</td><td>React 18, Vite, TypeScript, Axios</td></tr>
    <tr><td>Orchestrator</td><td>Go 1.22, Gin, Asynq (Redis), pgx, sqlc</td></tr>
    <tr><td>AI Engine</td><td>Python 3.12, FastAPI, sentence-transformers, gRPC</td></tr>
    <tr><td>Database</td><td>PostgreSQL 15 + pgvector</td></tr>
    <tr><td>Queue</td><td>Redis 7</td></tr>
    <tr><td>Packaging</td><td>Docker, PyInstaller (Python), WiX, dmg, deb</td></tr>
  </tbody>
</table>

<h2>📋 Road-map</h2>
<ul>
  <li>[ ] Live file-system watcher (fsnotify)</li>
  <li>[ ] OCR &amp; image embedding</li>
  <li>[ ] Optional cloud <strong>self-host</strong> sync (encrypted)</li>
  <li>[ ] Full-text + vector hybrid ranking</li>
  <li>[ ] Plug-in system (Go plug-ins / WASM)</li>
</ul>

<h2>🤝 Contributing</h2>
<ol>
  <li>Fork &amp; create a feature branch</li>
  <li>Add tests (Go: <code>*_test.go</code>, Python: <code>pytest</code>)</li>
  <li>Open a PR – CI runs lint + tests automatically</li>
</ol>

<h2>📄 License</h2>
<p>MIT – see <a href="LICENSE">LICENSE</a></p>
<p><strong>Star ⭐ the repo if you find it useful!</strong><br>Issues &amp; feedback welcome.</p>

</body>
</html>
