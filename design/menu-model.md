# MacHuna — menu model (native Swift port)

Reference only. See [README.md](README.md): this describes the eventual
mac-arsed Swift app, not the shipping Python app.

The mac-arsed skill's first rule is "build the command model before polishing
screens." This is that command model: the full menu bar for a native MacHuna,
grounded in what the app actually does. Format, standard, field order and play
options appear in the `Convert` menu *as well as* the settings panel, because
every important action should be reachable from the menu bar, not only from an
on-screen control. The same verbs also belong in each item's context menu.

Legend: `✓` = checkbox toggle · `(radio)` = mutually exclusive group · `▸` = submenu.

## MacHuna (app menu)
- About MacHuna (native About box, replaces the PyInstaller hack)
- Settings… ⌘,
- Services ▸
- Hide MacHuna / Hide Others / Show All
- Quit MacHuna ⌘Q

## File
- Open… ⌘O — a folder or files to convert
- Open Recent ▸ (recent items / Clear Menu)
- Add Files… ⌥⌘O — add to the current source list
- Close Window ⌘W
- Reveal Output in Finder ⇧⌘R

## Edit
- Undo / Redo ⌘Z / ⇧⌘Z — removing a queued item, a settings change
- Cut / Copy / Paste
- Copy Frame — current player frame to the pasteboard as an image
- Select All ⌘A
- Remove from List ⌫

## Convert (domain menu)
- Convert All ⌘R
- Convert Selected
- Stop ⌘. (Command-period, the Mac cancel convention)
- —
- Output Format ▸ (radio): Kahuna SWS · Kayenne EIF · Kayenne MOV · Kayenne TGA · Sony TGA · QuickTime MOV · TGA Sequence
- Video Standard ▸ (radio): 1080i/50 · 1080i/59.94 · 1080i/60 · 1080p/25 · 1080p/50 · 1080p/59.94 · 1080p/60
- Field Order ▸ (radio): TFF · BFF
- —
- Include Audio ✓
- Ignore Key ✓
- Auto Play ✓
- Loop Play ✓

## Player (context-sensitive — enabled when a Video Player window is frontmost)
- Open in Player ⌘Y — new player window for the selected item
- —
- Play / Pause (Space)
- Next Frame → / Previous Frame ←
- Go to Start / Go to End
- Loop ✓
- —
- Show Fill / Show Key / Show Composite (radio)
- Show Audio Meters ✓

## View
- Show / Hide Sidebar ⌃⌘S
- Show / Hide Conversion Log
- Enter Full Screen

## Window (standard macOS)
- Minimize ⌘M
- Zoom
- (list of open windows — main plus each player)
- Bring All to Front

## Help
- MacHuna Help — the user manual
- MacHuna User Manual — the PDF
- MacHuna on GitHub
- Report an Issue…

## Design notes

- **Convert options duplicated in the menu bar** is deliberate (mac-arsed: reachable everywhere). The settings panel stays the primary way to set them; the menu is the keyboard / muscle-memory path.
- **Player is context-sensitive**, greyed out until a player window is frontmost (as QuickTime does), keeping player verbs out of the way during conversion.
- **Context menus** on a source item should offer Convert, Open in Player, Reveal in Finder, Remove — toolbar, menu bar and right-click all pointing at the same commands.
- **Kept lean on purpose.** Restraint is a mac-arsed principle; no menu should exist just to look busy.
- Shortcuts above are first-pass conventions; finalise against real macOS defaults during the build to avoid clashes.
