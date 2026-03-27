  # Setup CLI – Development Roadmap
  
  This document defines the step-by-step plan for evolving the `setup` CLI into a modular, composable project scaffolding system.
  
  The goal is:
  - Fully composable templates (FastAPI, SQLAlchemy, Postgres, Alembic, Angular, etc.)
  - Clean separation between features
  - Optional Docker overlay (`--docker`)
  - Future support for remote Git-hosted templates
  
  ---
  
  # ?? Core Principles
  
  ## 1. Host-first architecture
  Without `--docker`, everything must:
  - Run locally
  - Have zero Docker dependencies
  - Be fully functional
  
  ## 2. Docker is an overlay
  `--docker`:
  - Adds deployment capability
  - Does NOT modify core logic
  - Generates compose partials only
  
  ## 3. Templates are independent
  Each template:
  - Owns only its domain
  - Does not assume other templates unless explicitly required
  - Can eventually live in its own Git repo
  
  ---
  
  # ?? Current State
  
  You currently have:
  
  ### CLI
  - `cli.py`
  - `planner.py`
  - `utils.py`
  
  ### Templates
  - base
  - backend-fastapi
  - db-sqlalchemy
  - db-postgres
  - alembic
  - frontend-angular
  
  ### Problems to Solve
  - Planner logic is ad-hoc
  - No formal dependency system
  - Template merging is fragile
  - Docker is mixed into templates (needs separation)
  - No automated validation/testing
  
  ---
  
  # ?? PHASE 1 — Planner System (CRITICAL)
  
  ## Goal
  Make template composition deterministic, validated, and scalable.
  
  ## Tasks
  
  ### 1. Template Registry
  Create a structured registry in `planner.py`:
  
  ```python
  TEMPLATES = {
      "backend-fastapi": {
          "provides": ["backend"],
          "requires": [],
      },
      "db-sqlalchemy": {
          "provides": ["sqlalchemy"],
          "requires": ["backend"],
      },
      "db-postgres": {
          "provides": ["postgres"],
          "requires": ["backend"],
      },
      "alembic": {
          "provides": ["migrations"],
          "requires": ["sqlalchemy"],
      },
  }
  
  
  
  
  2. Plan Resolution
  
  Implement:
  
  resolve_plan(flags) -> list[Template]
  validate_plan(plan)
  
  Validation rules:
  •	alembic requires db-sqlalchemy
  •	Only one DB provider allowed
  •	Backend must exist before DB
  
  
  
  3. Debug Output
  
  Always print:
  
  Selected flags:
  Resolved plan:
   - base
   - backend-fastapi
   - db-sqlalchemy
   - db-postgres
   - alembic
  
  
  
  
   PHASE 2 — Template Merge System
  
  Problem
  
  Multiple templates modify same files ? fragile overwrites.
  
  Solution
  
  Central merge utilities.
  
  
  
  Tasks
  
  1. Add to utils.py
  
  merge_toml(base_file, patch_file)
  merge_env(base_env, patch_env)
  
  
  
  
  2. Standardize patch files
  
  Example:
  
  backend/pyproject.patch.toml.jinja
  backend/.env.patch
  
  
  
  
  3. Apply patches after Copier runs
  
  Flow:
  
  Copy template ? apply patches ? finalize
  
  
  
  
   PHASE 3 — Docker Overlay (Clean Separation)
  
  Goal
  
  Docker should be OPTIONAL and modular.
  
  
  
  Remove from current templates:
  •	docker-compose.yml
  •	Dockerfile
  
  Move them into new templates:
  
  templates/
    docker-api/
    docker-postgres/
  
  
  
  
  Docker Behavior
  
  Without --docker
  •	No docker files generated
  •	User runs everything locally
  
  
  
  With --docker
  
  Generate:
  
  compose.yaml
  compose/
    api.yaml
    postgres.yaml
  
  
  
  
  Compose Structure
  
  Root file
  
  include:
    - compose/api.yaml
    - compose/postgres.yaml
  
  
  
  
  API Partial
  •	No DB hardcoding
  •	Uses DATABASE_URL
  
  
  
  Postgres Partial
  •	Defines db service
  •	Exposes port (auto-picked)
  
  
  
  CLI Responsibilities
  
  When --docker:
  •	Apply docker templates
  •	Generate compose.yaml
  •	Pick free ports
  •	Write .env
  
  
  
   PHASE 4 — Fast vs Full Mode
  
  Define behavior
  
  --fast
  •	Skip installs
  •	Skip docker
  •	Skip migrations
  •	Only generate files
  
  
  
  Default mode
  •	Full generation
  •	Optional future:
  •	run migrations
  •	start services
  
  
  
  Add:
  
  --dry-run
  
  Print plan without writing files.
  
  
  
   PHASE 5 — Testing System
  
  Add pytest
  
  Tests:
  •	Generate project in temp dir
  •	Assert:
  •	files exist
  •	correct structure
  •	expected content
  
  
  
  Matrix tests
  •	fastapi only
  •	fastapi + sqlalchemy
  •	fastapi + postgres
  •	full stack
  
  
  
   PHASE 6 — Runnable “Golden Path”
  
  Goal
  
  Generated project must WORK immediately.
  
  
  
  Backend
  •	/health route
  •	DB session configured
  
  
  
  Alembic
  •	connected to Base.metadata
  •	can autogenerate migrations
  
  
  
  Optional CLI flag
  
  --smoke
  
  Runs:
  •	docker db
  •	alembic check
  •	api boot test
  
  
  
   PHASE 7 — Presets
  
  Add:
  
  --preset fastapi-postgres
  --preset fullstack-angular
  
  Presets expand into flags internally.
  
  
  
   PHASE 8 — Versioning + Future Git Templates
  
  Goal
  
  Allow templates to live in separate repos later.
  
  
  
  Step 1 (now)
  
  Add metadata file:
  
  .setup-cli.lock
  
  Example:
  
  {
    "templates": {
      "backend-fastapi": "local",
      "db-postgres": "local"
    }
  }
  
  
  
  
  Step 2 (future)
  
  Support:
  
  setup demo --template backend-fastapi=github:org/repo
  
  
  
  
   PHASE 9 — Documentation
  
  Update README
  
  Include:
  •	install instructions
  •	examples
  •	explanation of plan
  •	how to add templates
  
  
  
   Suggested Execution Order
  1.	Planner registry + validation
  2.	Debug plan output
  3.	Merge system
  4.	Remove Docker from templates
  5.	Add docker overlay system
  6.	Add tests
  7.	Add presets
  8.	Add versioning
  9.	Improve docs
  
  
  
   End Goal
  
  You will have:
  •	A composable CLI like:
  
  setup demo --fastapi --sqlalchemy --postgres --alembic
  setup demo --preset fullstack --docker
  
  •	Clean architecture:
  •	templates = independent units
  •	docker = optional overlay
  •	planner = single source of truth
  •	Ready for:
  •	Git-hosted templates
  •	plugin ecosystem
  •	AST-based generators later
  
  
  
   Notes
  •	Keep everything deterministic
  •	Avoid “magic merging”
  •	Favor explicit structure over clever automation
  •	Always validate before generating
  
