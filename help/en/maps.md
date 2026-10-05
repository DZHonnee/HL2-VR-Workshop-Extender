# Maps

## Why unpack?
<p>If map addons are mounted like regular addons, then in the VR mod these maps will be missing some textures and models because the game, for some reason, cannot properly read map files if they are packed in .vpk archives like all regular addons. The problem is solved by unpacking the archive and mounting this unpacked folder instead of the .vpk file in gameinfo.txt.</p>

<h2>Map unpacking error</h2>
<p>In case of error, try alternative unpacking method:</p>
<ol>
    <li>Open the tool folder and go to the <b>alt_vpk_extractor</b> folder</li>
    <li>Open the problematic addon's folder</li>
    <li>Find the <b>workshop_dir.vpk</b> file</li>
    <li>Drag it onto the <b>vpk.exe</b> file in the previously opened tool folder and wait for unpacking</li>
    <li>Press <b>Refresh list (⟳)</b> and see if status changed to UNPACKED</li>
</ol>