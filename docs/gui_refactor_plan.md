# GUI Refactoring Plan

## Objectives
- Align the wxPython GUI with SOLID/DRY/KISS principles while keeping behaviour intact.
- Reduce coupling between the window classes and application logic to improve testability.
- Replace dynamic, implicit wiring with explicit, declarative structures that are easier to reason about.
- Maintain a TDD-first workflow and expand automated coverage around any refactored surface area.

## Current Pain Points (Baseline)
- `phatch/pyWx/gui.py`'s `Frame` class exceeds 1,200 lines and combines responsibilities for application state, persistence, view rendering, plugin integration, and event wiring.
- Domain logic lives inside view mixins (`DialogsMixin.load_actionlist_data`, `_execute`, `_save`), coupling wx widgets to `core.api` calls and making headless testing hard.
- Menu/toolbar creation relies on introspection and runtime binding via `types.MethodType`, which obscures intent and risks accidental breakage.
- Help/documentation menu handlers repeat nearly identical `webbrowser.open` calls, violating DRY.
- Dirty state toggles via string truthiness (`''`/`'*'`), making the window title logic fragile.

## Refactoring Phases

### Phase 1 — Introduce GUI Application Services
- Define an explicit service layer (e.g., `ActionListService`) that encapsulates load/save/execute logic now embedded in `Frame`/`DialogsMixin`.
- Move file-history management and notification triggering into the service where possible, exposing clear methods for the view to call.
- Back the new service with unit tests that exercise action list workflows without wx dependencies (mock `core.api` as needed).
- Update `Frame` to depend on the service through composition or dependency injection, slimming constructor responsibilities.

### Phase 2 — Extract Controller & State Objects
- Create a dedicated controller (e.g., `ActionListController`) for orchestrating interactions between the tree widget, dialogs, and the service.
- Introduce lightweight state/value objects for window state (dirty flag, selected action list path) to avoid indirect string flags.
- Migrate event handlers to the controller; keep the wx frame focused on rendering and delegating.
- Cover controller logic with tests where possible (pure Python, no wx calls).

### Phase 3 — Declarative Menu & Toolbar Builders
- Replace dynamic `dir(self)` scanning and ad-hoc handler registration with declarative menu/toolbar descriptors.
- Implement builder helpers that accept data structures and wire up menu items/tool buttons plus handlers in one place.
- Consolidate repeated handler bodies (e.g., Execute/Add/Remove/Move commands) into controller methods to keep wiring thin.
- Add regression tests for builder helpers (ensure descriptors generate expected IDs/actions).

### Phase 4 — Clean Up Repeated Helpers & Constants
- Collapse the help/documentation handlers into a shared map + helper function, aligning the existing URLs and easing future changes.
- Audit for additional repeated snippets (e.g., file dialogs) and move them into reusable utility functions or mixins.
- Ensure all reused helpers have small, focused tests.

### Phase 5 — Polish & Backfill Tests
- Revisit `DialogsMixin` and wxGlade-derived dialogs to delegate complex logic to the new services/controller.
- Tighten dirty-state handling by introducing explicit boolean flags and deriving UI indicators from them.
- Expand integration-style GUI tests where feasible (e.g., smoke tests using `wx.App` in headless mode) while keeping fast, deterministic core tests.

## Tooling & Workflow
- Continue running `pytest` and `ruff` per change set; add targeted unit tests alongside each refactor.
- Leverage existing static analysis (ruff, upcoming Vulture pass) to catch dead code once the extraction settles.
- Commit in small, reviewable increments per phase to keep regressions manageable.

## Open Questions / Dependencies
- Determine whether optional dependencies (e.g., droplet installers) need shim interfaces in the new service layer.
- Confirm test harness support for wx event loop in CI before adding GUI smoke tests.
- Decide whether to retain backward compatibility with legacy config keys when restructuring settings/state objects.

