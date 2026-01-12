# Maps

## What's the problem?
<p>If map addons are mounted like regular addons, then in VR mod these maps will be missing some textures and models because 
the game for some reason can't properly read map files if they're packed in .vpk archives like all regular addons. 
The problem is solved by unpacking the archive and mounting this unpacked folder instead of the .vpk file in gameinfo.txt, which is done through the check function.</p>

## How does checking work?
<p>The tool checks the addon's Steam workshop page for the maps tag. 
The addon is marked with a MAP label and you're prompted to unpack this addon, after which, if agreed, the addon is unpacked in its folder and the link in gameinfo.txt is updated.</p>

<h3>Check functions</h3>
<ul>
    <li><b>Automatically (checkbox)</b> - only checks addons that are currently being mounted</li>
    <li><b>"Check maps" button</b> - checks all addons in the list</li>
    <li><b>Right click → "Check map"</b> - check individual addon through context menu</li>
    <br><li><b>Clear maps</b> - delete all unpacked folders, change paths in gameinfo.txt back to .vpk</li>
</ul>

<h2>Map unpacking error</h2>
<p>In case of error, try alternative unpacking method:</p>
<ol>
    <li>Open the tool folder and go to the <b>alt_vpk_extractor</b> folder</li>
    <li>Open the problematic addon's folder</li>
    <li>Find the <b>workshop_dir.vpk</b> file</li>
    <li>Drag it onto the <b>vpk.exe</b> file in the previously opened tool folder and wait for unpacking</li>
    <li>Perform <b>Check map</b> for this addon</li>
</ol>