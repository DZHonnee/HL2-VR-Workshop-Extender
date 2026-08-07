# HL2:VR Workshop Extender

## Program purpose
<p>This tool allows you to conveniently mount addons from Half-Life 2's workshop into Half-Life 2: VR Mod and its Episodes, while providing basic management features. 
Works ONLY with the Half-Life 2 workshop!</p>

<p><b>(!) Addons from Half-Life 2: VR Mod (or Episodes) workshop and addons in the "custom" folder always take priority over addons mounted through this tool.</b></p>

<p>Please note that this tool is essentially a collection of workarounds, so proper functionality of every mod is not guaranteed. It works best with reskins, simple maps and mods that doesn't use any custom content besides models and textures (see <b>Maps</b> and <b>Recommendations and issues</b> tabs).</p>

## Main features
<ul>
    <li>Mounting installed addons</li>
    <li>Mounting addons from Steam workshop collections</li>
    <li>Mounting individual addons</li>
    <li>Mounting addons into Episodes</li>
    <li>Managing addon load order</li>
    <li>Verifying addon file existence</li>
    <li>Maintaining map addons functionality</li>
    <li>Saving and loading addon lists</li>
    <li>Installing Anniversary Update content</li>
    <li>(NEW) Mounting non-workshop (external) mods alongside the workshop ones</li>
</ul>

<p>Check the following tabs for explanations of all features.</p>

<h2>How it works</h2>
<p>
The tool doesn't download or copy anything, but mounts already downloaded Steam addons. This process works as follows:
</p>
<ol>
    <li>The tool retrieves addon IDs either from their Steam page or from workshop.txt (HL2's addon list file)</li>
    <li>Uses these IDs to locate addon files in the Half-Life 2 workshop folder (*\\steamapps\\workshop\\content\\220)</li>
    <li>Inserts these paths into Half-Life 2 VR's gameinfo.txt file, instructing the game to use this content</li>
</ol>


<p><br><br>If you encounter any issues or have questions you can create an issue on GitHub, contact me on Discord (@dzhonnee) or Steam (https://steamcommunity.com/id/dzhonnee/)</p>

