"""
Workflow Management MCP Presentation Layer

This module provides FastMCP tools for workflow management operations,
including file-based import/export functionality.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import Context, FastMCP

from services.services import get_workflow_management_service

# Add the parent directory to the path so we can import from the main app
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Create the MCP server for workflow management operations
mcp = FastMCP("Workflow Management")


@mcp.tool
async def export_workflows_to_file(
    entity_name: str,
    model_version: str,
    file_path: str,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Export all workflow configurations for an entity model to a local JSON file.

    Because a single entity type can have multiple workflows (Cyoda selects the applicable
    one at runtime using each workflow's top-level `criterion`), the response is
    always a collection — even if only one workflow is configured.

    The exported file contains a JSON array of workflow configuration objects.
    The full request and response shapes are defined in
    `docs/cyoda/openapi-workflow.yml`. Each configuration includes:
      - name / desc       : human-readable identity (name is unique per model)
      - version           : workflow configuration version (currently "1.0")
      - initialState      : the state assigned to a new entity entering the workflow
      - active            : whether the workflow is live
      - criterion         : optional condition that selects which entities use this
                            workflow (simple / group / function QueryCondition)
      - states            : map of state-code → state definition, where each state
                            lists the transitions available from it:
          - name     : transition identifier (used when calling update_entity)
          - next     : target state after the transition
          - manual   : true = caller must trigger; false = Cyoda fires automatically
          - disabled : optional flag to suppress a transition without deleting it
          - criterion: optional condition that must be satisfied for the transition
                       to fire (supports simple / group / function types)
          - processors: zero or more processors to execute on the transition:
              - externalized: calls out to your gRPC processor with execution
                              modes SYNC, ASYNC_SAME_TX, or ASYNC_NEW_TX
              - scheduled   : fires a delayed automatic transition after delayMs

    The file is written as a pretty-printed JSON array. Relative `file_path`
    values are resolved from the project root. Parent directories are created
    automatically if they do not exist. The file can be edited and re-imported
    with `import_workflows_from_file`.

    Args:
        entity_name: Name of the entity model (e.g. "Customer").
        model_version: Version of the entity model (e.g. "1").
        file_path: Destination path for the JSON file. Relative paths resolve
                   from the project root (e.g. "application/resources/workflow/customer/version_1/workflow.json").
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on success
          - file_path: absolute path the file was written to
          - workflows_count: number of workflows exported
          - entity_name / model_version: echoed back
    """
    try:
        if ctx:
            await ctx.info(
                f"Exporting workflows for entity {entity_name} version {model_version} to {file_path}"
            )

        # Get workflows from Cyoda
        workflow_management_service = get_workflow_management_service()
        export_result = await workflow_management_service.export_entity_workflows(
            entity_name=entity_name, model_version=model_version
        )

        if not export_result.get("success", False):
            return export_result

        workflows = export_result.get("workflows", [])
        if not workflows:
            return {
                "success": False,
                "error": f"No workflows found for entity {entity_name} version {model_version}",
                "entity_name": entity_name,
                "model_version": model_version,
            }

        # Resolve file path (relative to project root if not absolute)
        if not os.path.isabs(file_path):
            # Get project root (3 levels up from this file)
            project_root = Path(__file__).parent.parent.parent
            full_path = project_root / file_path
        else:
            full_path = Path(file_path)

        # Create directory if it doesn't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write workflows to file
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(workflows, f, indent=2, ensure_ascii=False)

        if ctx:
            await ctx.info(
                f"Successfully exported {len(workflows)} workflows to {full_path}"
            )

        return {
            "success": True,
            "message": f"Exported {len(workflows)} workflows to {full_path}",
            "file_path": str(full_path),
            "workflows_count": len(workflows),
            "entity_name": entity_name,
            "model_version": model_version,
        }

    except Exception as e:
        error_msg = f"Failed to export workflows to file: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "entity_name": entity_name,
            "model_version": model_version,
            "file_path": file_path,
        }


@mcp.tool
async def import_workflows_from_file(
    entity_name: str,
    model_version: str,
    file_path: str,
    import_mode: str = "REPLACE",
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Import workflow configurations from a local JSON file into Cyoda.

    Workflow names are unique per entity model: importing a workflow whose name already
    exists updates that workflow; importing a new name creates it.

    The file must contain a JSON array of workflow configuration objects (a
    single object is also accepted and wrapped automatically). Required fields
    per workflow: `version`, `name`, `initialState`, `states`. The full schema
    is defined in `docs/cyoda/openapi-workflow.yml`.

    Use `validate_workflow_file` to check the file structure before
    importing. Use `export_workflows_to_file` to obtain a valid template
    from an existing entity model.

    Import modes
    ------------
    REPLACE  (default) — Removes all existing workflows for the entity and
             keeps only the imported ones. Also deletes any processors and
             criteria that are no longer referenced by any workflow.
             Use when you want the Cyoda configuration to exactly match the
             file, with no leftover artefacts.

    ACTIVATE — Like REPLACE, but deactivates other workflows and transitions
               instead of deleting them. Unused processors and criteria are
               preserved. Use when you need a clean active set but want to
               retain history or the ability to reactivate old workflows.

    MERGE    — Performs an incremental update of only the workflows listed in
               the file. Workflows not mentioned remain completely unchanged.
               Use for targeted changes to a subset of an entity's workflows.

    *** REPLACE deletes data — use with caution on production environments.
    Export first to create a backup if needed. ***

    File path resolution: relative paths are resolved from the project root.
    The conventional layout is:
      application/resources/workflow/{entityName}/version_{version}/workflow.json

    Args:
        entity_name: Name of the entity model (e.g. "Customer").
        model_version: Version of the entity model (e.g. "1").
        file_path: Path to the JSON workflow file. Relative paths resolve from
                   the project root.
        import_mode: One of "REPLACE" (default), "ACTIVATE", or "MERGE".
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on success
          - file_path: absolute path the file was read from
          - workflows_loaded: number of workflow definitions sent to Cyoda
          - entity_name / model_version: echoed back
    """
    try:
        if ctx:
            await ctx.info(
                f"Importing workflows for entity {entity_name} version {model_version} from {file_path}"
            )

        # Resolve file path (relative to project root if not absolute)
        if not os.path.isabs(file_path):
            # Get project root (3 levels up from this file)
            project_root = Path(__file__).parent.parent.parent
            full_path = project_root / file_path
        else:
            full_path = Path(file_path)

        # Check if file exists
        if not full_path.exists():
            return {
                "success": False,
                "error": f"Workflow file not found: {full_path}",
                "entity_name": entity_name,
                "model_version": model_version,
                "file_path": file_path,
            }

        # Read workflows from file
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                workflow = json.load(f)
                workflows = workflow if isinstance(workflow, list) else [workflow]
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON in workflow file: {str(e)}",
                "entity_name": entity_name,
                "model_version": model_version,
                "file_path": str(full_path),
            }

        # Validate workflows is a list
        if not isinstance(workflows, list):
            return {
                "success": False,
                "error": "Workflow file must contain a JSON array of workflow definitions",
                "entity_name": entity_name,
                "model_version": model_version,
                "file_path": str(full_path),
            }

        if ctx:
            await ctx.info(f"Loaded {len(workflows)} workflows from {full_path}")

        # Import workflows to Cyoda
        workflow_management_service = get_workflow_management_service()
        import_result = await workflow_management_service.import_entity_workflows(
            entity_name=entity_name,
            model_version=model_version,
            workflows=workflows,
            import_mode=import_mode,
        )

        # Enhance result with file information
        if import_result.get("success", False):
            import_result["file_path"] = str(full_path)
            import_result["workflows_loaded"] = len(workflows)
            if ctx:
                await ctx.info(
                    f"Successfully imported {len(workflows)} workflows from {full_path}"
                )

        return import_result

    except Exception as e:
        error_msg = f"Failed to import workflows from file: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "entity_name": entity_name,
            "model_version": model_version,
            "file_path": file_path,
        }


@mcp.tool
async def list_workflow_files(
    base_path: str = "application/resources/workflow",
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    List workflow JSON files on the local filesystem under a base directory.

    This is a local file operation — it does not contact the Cyoda API. Use it
    to discover which workflow files are available for import, or to confirm
    that an export landed where expected.

    Files are discovered recursively. For each `.json` file found the tool
    reports:
      - file_path / relative_path / file_name: location on disk
      - size_bytes: file size
      - entity_name / model_version: inferred from the directory structure when
        the path follows the convention
        `{base}/{entityName}/version_{version}/...`
      - workflows_count: number of workflow objects in the file
      - workflow_name / workflow_version: taken from the first workflow object

    The conventional base directory used by this project is
    "application/resources/workflow". Relative `base_path` values are resolved
    from the project root.

    Args:
        base_path: Directory to search (default "application/resources/workflow").
                   Relative paths resolve from the project root.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on success
          - base_path: absolute path that was searched
          - files_count: total number of JSON files found
          - workflow_files: list of file descriptor objects (see above)
    """
    try:
        if ctx:
            await ctx.info(f"Listing workflow files in {base_path}")

        # Resolve base path (relative to project root if not absolute)
        if not os.path.isabs(base_path):
            # Get project root (3 levels up from this file)
            project_root = Path(__file__).parent.parent.parent
            full_base_path = project_root / base_path
        else:
            full_base_path = Path(base_path)

        if not full_base_path.exists():
            return {
                "success": False,
                "error": f"Directory not found: {full_base_path}",
                "base_path": base_path,
            }

        # Find all JSON files recursively
        workflow_files = []
        for json_file in full_base_path.rglob("*.json"):
            relative_path = json_file.relative_to(full_base_path)

            # Try to extract entity info from path structure
            path_parts = relative_path.parts
            entity_info = {
                "file_path": str(json_file),
                "relative_path": str(relative_path),
                "file_name": json_file.name,
                "size_bytes": json_file.stat().st_size,
            }

            # Try to parse entity name and version from directory structure
            if len(path_parts) >= 2:
                entity_info["entity_name"] = path_parts[0]
                if path_parts[1].startswith("version_"):
                    entity_info["model_version"] = path_parts[1].replace("version_", "")

            # Try to read basic workflow info
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    workflow_data = json.load(f)
                    if isinstance(workflow_data, list) and workflow_data:
                        entity_info["workflows_count"] = len(workflow_data)
                        # Get info from first workflow if available
                        first_workflow = workflow_data[0]
                        if isinstance(first_workflow, dict):
                            entity_info["workflow_name"] = first_workflow.get("name")
                            entity_info["workflow_version"] = first_workflow.get(
                                "version"
                            )
                    elif isinstance(workflow_data, dict):
                        entity_info["workflows_count"] = 1
                        entity_info["workflow_name"] = workflow_data.get("name")
                        entity_info["workflow_version"] = workflow_data.get("version")
            except (json.JSONDecodeError, IOError):
                entity_info["error"] = "Could not read workflow file"

            workflow_files.append(entity_info)

        # Sort by entity name and version
        workflow_files.sort(
            key=lambda x: (
                x.get("entity_name", ""),
                x.get("model_version", ""),
                x.get("file_name", ""),
            )
        )

        if ctx:
            await ctx.info(f"Found {len(workflow_files)} workflow files")

        return {
            "success": True,
            "base_path": str(full_base_path),
            "files_count": len(workflow_files),
            "workflow_files": workflow_files,
        }

    except Exception as e:
        error_msg = f"Failed to list workflow files: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "base_path": base_path,
        }


@mcp.tool
async def validate_workflow_file(
    file_path: str,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Validate a local workflow JSON file for structural correctness before importing.

    This is a local file operation — it does not contact the Cyoda API.
    Run this before `import_workflows_from_file` to catch obvious errors
    early and avoid a failed import.

    Checks performed:
      - File exists and contains valid JSON
      - Top-level value is a workflow object or array of workflow objects
      - Each workflow contains the required fields: `name` and `states`
      - Each state definition is a dictionary
      - Each state's `transitions` value (if present) is an array

    Note: this tool validates local structure only. It does not check that
    referenced processor names, criterion functions, or state names are
    registered in Cyoda. A file that passes this check may still be rejected
    by the API if, for example, `initialState` references a state not defined
    in `states`, or a processor name does not match any registered gRPC handler.

    Required fields per workflow (see `docs/cyoda/openapi-workflow.yml`):
      - version      : workflow configuration version (use "1.0")
      - name         : unique identifier within the entity model
      - initialState : state code assigned to newly created entities
      - states       : map of state-code → {transitions: [...]}

    Args:
        file_path: Path to the workflow JSON file. Relative paths resolve from
                   the project root.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success / is_valid: True if no structural errors were found
          - workflows_count: number of workflow objects detected
          - structure: "array" or "single_object"
          - errors: list of structural error messages (empty on success)
          - warnings: list of non-fatal observations
          - file_path / file_size: file metadata
    """
    try:
        if ctx:
            await ctx.info(f"Validating workflow file: {file_path}")

        # Resolve file path (relative to project root if not absolute)
        if not os.path.isabs(file_path):
            # Get project root (3 levels up from this file)
            project_root = Path(__file__).parent.parent.parent
            full_path = project_root / file_path
        else:
            full_path = Path(file_path)

        # Check if file exists
        if not full_path.exists():
            return {
                "success": False,
                "error": f"Workflow file not found: {full_path}",
                "file_path": file_path,
            }

        # Read and parse JSON
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                workflow_data = json.load(f)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON in workflow file: {str(e)}",
                "file_path": str(full_path),
            }

        validation_result: Dict[str, Any] = {
            "success": True,
            "file_path": str(full_path),
            "file_size": full_path.stat().st_size,
            "warnings": [],
            "errors": [],
        }

        # Type-safe access to lists
        errors: List[str] = validation_result["errors"]

        # Validate structure
        if isinstance(workflow_data, list):
            validation_result["workflows_count"] = len(workflow_data)
            validation_result["structure"] = "array"

            # Validate each workflow in the array
            for i, workflow in enumerate(workflow_data):
                if not isinstance(workflow, dict):
                    errors.append(f"Workflow {i} is not a dictionary")
                    continue

                # Check required fields
                required_fields = ["name", "states"]
                for field in required_fields:
                    if field not in workflow:
                        errors.append(f"Workflow {i} missing required field: {field}")

                # Check states structure
                if "states" in workflow and isinstance(workflow["states"], dict):
                    for state_name, state_data in workflow["states"].items():
                        if not isinstance(state_data, dict):
                            errors.append(
                                f"Workflow {i}, state '{state_name}' is not a dictionary"
                            )
                        elif "transitions" in state_data and not isinstance(
                            state_data["transitions"], list
                        ):
                            errors.append(
                                f"Workflow {i}, state '{state_name}' transitions must be an array"
                            )

        elif isinstance(workflow_data, dict):
            validation_result["workflows_count"] = 1
            validation_result["structure"] = "single_object"

            # Check required fields for single workflow
            required_fields = ["name", "states"]
            for field in required_fields:
                if field not in workflow_data:
                    errors.append(f"Workflow missing required field: {field}")

            # Check states structure
            if "states" in workflow_data and isinstance(workflow_data["states"], dict):
                for state_name, state_data in workflow_data["states"].items():
                    if not isinstance(state_data, dict):
                        errors.append(f"State '{state_name}' is not a dictionary")
                    elif "transitions" in state_data and not isinstance(
                        state_data["transitions"], list
                    ):
                        errors.append(
                            f"State '{state_name}' transitions must be an array"
                        )
        else:
            errors.append(
                "Workflow file must contain either a workflow object or array of workflows"
            )

        # Set overall success based on errors
        validation_result["success"] = len(errors) == 0
        validation_result["is_valid"] = validation_result["success"]

        if ctx:
            if validation_result["success"]:
                await ctx.info(
                    f"Workflow file is valid: {validation_result['workflows_count']} workflows found"
                )
            else:
                await ctx.error(
                    f"Workflow file validation failed: {len(errors)} errors found"
                )

        return validation_result

    except Exception as e:
        error_msg = f"Failed to validate workflow file: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "file_path": file_path,
        }
