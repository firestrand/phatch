# GUI Refactoring Plan

## Objectives
- Align the wxPython GUI with SOLID/DRY/KISS principles while keeping behaviour intact. ✅
- Reduce coupling between the window classes and application logic to improve testability. ✅
- Replace dynamic, implicit wiring with explicit, declarative structures that are easier to reason about. ✅
- Maintain a TDD-first workflow and expand automated coverage around any refactored surface area. ✅

## Current State (Spring 2025)
- The monolithic `Frame` constructor has been pared back: service wiring now flows through `FrameDependencies`, and GUI-facing logic lives in dedicated helpers (`DialogService`, `FileMenuCoordinator`, `DropletManager`, `ActionListController`).
- Domain operations were migrated into service objects; `DialogsMixin` delegates to `ActionListService` and `DialogService`, allowing most workflows to be unit-tested without wx.
- Declarative descriptors (`ui_descriptors.py` + `file_menu.py`) drive menu/toolbar creation, replacing `dir(self)` scans and ad-hoc method binding.
- Documentation/help handlers are centralised in `ui_descriptors.HELP_LINKS`, eliminating repeated `webbrowser.open` calls.
- Dirty-state handling now uses explicit controller state and window-title helpers; string truthiness is no longer the primary mechanism.

## Refactoring Phases

### Phase 1 — Introduce GUI Application Services ✅
- `ActionListService` already encapsulates load/save/execute flows and is covered by unit tests.
- `DialogService` now owns dialog/notification orchestration, decoupling mixins from wx.
- File history and clipboard interaction moved into `FileMenuCoordinator` (see Phase 3).
- `FrameDependencies` injects these services into `Frame`, `DropletApp`, and `DropletFrame`.

### Phase 2 — Extract Controller & State Objects ✅
- `ActionListController` manages action-tree state transitions and is thoroughly unit-tested (`tests/unit/app/test_action_list_controller.py`).
- Window state (filename, dirty flag, description) now lives inside the controller’s `ActionListState`.
- Frame/event handlers delegate to the controller, keeping wx-specific glue thin.

### Phase 3 — Declarative Menu & Toolbar Builders ✅
- `ui_descriptors.py` and `file_menu.py` describe menus/toolbars declaratively.
- `FileMenuCoordinator` consolidates the Open/Save/Export flows and history management; unit tests back the coordinator.
- Toolbar/menu enablement derives from descriptor groups instead of direct attribute scanning.

### Phase 4 — Clean Up Repeated Helpers & Constants (In Progress)
- `ui_descriptors.HELP_LINKS` consolidates documentation handlers.
- `FileDialogService` wraps wx dialogs for reuse; file-menu actions call into it through the coordinator.
- TODO: extract remaining notification/report helpers from `DialogsMixin` into focused services.
- TODO: continue trimming legacy mixins (e.g., progress dialogs) now that service hooks exist.

### Phase 5 — Polish & Backfill Tests (In Progress)
- Added deterministic unit tests for services (`DialogService`, `FileMenuCoordinator`, `FrameDependencies`, slider controls) and an ActionList round-trip integration test.
- Introduced a wx-gated GUI smoke test scaffold (`tests/integration/test_gui_smoke.py`); enable it in environments with wxPython installed.
- TODO: expand smoke coverage once headless wx testing is available in CI.
- TODO: audit remaining wxGlade mixins for logic extraction opportunities.

## Tooling & Workflow
- `pytest` remains the primary regression gate; integration tests cover action list round trips and all actions.
- `ruff` and `licensecheck` tests now skip gracefully when tools are missing, encouraging contributors to install optional dev dependencies locally.
- New tests live beside the features they exercise, keeping change sets reviewable.

## Open Questions / Next Steps
- Extract remaining notification/progress helpers from `DialogsMixin` into dedicated services.
- Investigate CI-friendly wxPython setup so GUI smoke tests can run automatically.
- Finalise documentation around dependency injection so new contributors avoid reintroducing tight coupling.
- Audit legacy config keys before restructuring settings/state objects.
