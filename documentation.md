# IsometKit Documentation

This document provides more detailed instructions and technical insights into using and managing the IsometKit add-on for Blender.

## Overview

IsometKit is built to provide an out-of-the-box solution for isometric art generation in Blender (version 5.0+). It abstracts away the tedious parts of asset importing, camera positioning, and surface alignment.

## The Asset Pipeline

IsometKit loads `.blend` files dynamically from the `assets/` directory included in the add-on folder.
When the add-on is loaded, or when the **Refresh Assets** button is clicked, it:
1. Scans the `assets` folder.
2. Looks for accompanying thumbnails in the `thumbnails` folder. If none are found, it generates them via a background render.
3. Groups objects based on keyword categorization into `Furniture`, `Tech`, `Plants`, and `Props`.
4. Exposes them in the UI with a search filter.

## Placement Controls Reference

When clicking **Place Asset**, the addon enters a modal state (interactive placement mode). 

- **Mouse Movement**: Moves the object along the surface under the cursor.
- **Left Mouse Button (LMB)**: Confirms the final position of the asset.
- **Right Mouse Button / ESC**: Cancels placement and removes the object.
- **Scroll Wheel**: Scales the object uniformly.
- **Ctrl + Scroll Wheel**: Rotates the object around its local Z-axis.
- **Shift + Vertical drag**: Scales the object (trackpad friendly).
- **Ctrl + Shift + Vertical drag**: Rotates the object (trackpad friendly).
- `+` / `-` Keys: Alternative way to scale.

### "Align to Target" Feature
When **Align to Target** is checked in the UI, IsometKit will raycast against the scene and automatically align the Z-axis of the placed asset to match the normal of the face it is hovering over. Furthermore, it snaps to cardinal axes for perfect isometric consistency.

## Environment Generators

- **Generate Iso Setup**: Creates a camera named `IsoCamera` set to *Orthographic* mode, angled precisely at [60°, 0°, 45°] to achieve a classic isometric projection.
- **Generate Simple Light Setup**: Spawns a soft sunlight angled to provide pleasant isometric shading, along with minimal ambient fill light.

## Troubleshooting

- **Thumbnails not appearing**: Click the refresh icon next to the Asset Loader label. Make sure your Blender installation can run background processes for rendering thumbnails.
- **Missing Categories**: Ensure your object names within the `.blend` file contain recognizable keywords (e.g., "chair", "plant", "laptop").
- **Asset not snapping correctly**: Ensure the target object you are placing onto has applied scale (`Ctrl+A` -> Scale) and clean geometry.

## Contact

For bug reports or feature requests, visit the [GitHub repository](https://github.com/TheEmber1).
