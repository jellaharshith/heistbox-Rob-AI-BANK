"""Start the installed Blender MCP in a separate, unsaved Blender session."""
import bpy
import addon_utils

addon_utils.enable('blender_mcp', default_set=False, persistent=False)
bpy.ops.blendermcp.start_server()
print('Character preview MCP ready')
