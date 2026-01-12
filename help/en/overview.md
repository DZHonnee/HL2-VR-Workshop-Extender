# HL2:VR Workshop Extender

## Program purpose
<p>This tool allows you to conveniently mount addons from Half-Life 2's workshop into Half-Life 2: VR Mod and its Episodes, while providing basic management features. 
Works ONLY with the Half-Life 2 workshop!</p>

<p><b>(!) Addons from Half-Life 2: VR Mod (or Episodes) workshop and addons in the "custom" folder always take priority over addons mounted through this tool.</b></p>

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
</ul>

<p>Check the following tabs for explanations of all features.</p>

<h2>How it works</h2>
<p>
The tool doesn't download anything, but mounts already downloaded Steam addons. This process works as follows:
</p>
<ol>
    <li>The tool retrieves addon IDs either from their Steam page or from workshop.txt (HL2's addon list file)</li>
    <li>Uses these IDs to locate addon files in the Half-Life 2 workshop folder (*\\steamapps\\workshop\\content\\220)</li>
    <li>Inserts these paths into Half-Life 2 VR's gameinfo.txt file between special markers, instructing the game to use this content</li>
</ol>

<p><br><br>If you encounter any issues or have questions you can create an issue on GitHub, contact me on Discord (@dzhonnee) or Steam (https://steamcommunity.com/id/dzhonnee/)</p>