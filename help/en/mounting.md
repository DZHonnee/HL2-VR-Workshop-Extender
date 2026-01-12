# Mounting addons

## Mounting methods

### 1. Installed addons
<p>Mounts addons you're subscribed to that are present in the Half-Life 2 addon list, maintaining their order. 
Note that addons only appear in the Half-Life 2 addon list if you enter the game after subscribing, or if you subscribe with the game running.
<br><b>(!)</b> This function doesn't mount map addons that appear in HL2 as separate campaigns. 
Mount them as individual addons or create a collection from your addons and mount it.
<br>P.S. During the loading process, you may notice in the logs that some addons are loaded in the wrong order (e.g., 1/5, 3/5, 5/5, 4/5, 2/5).
This is normal behavior, as multi-threaded processing is occurring. The final list will still be created in the correct order, matching the HL2 list.
</p>

### 2. Workshop collections
<p>Mounts addons from a collection in REVERSE order because this is exactly how they appear in HL2 after the collection is loaded. 
Collection creators assemble their collections specifically with reverse order in mind (lower position - higher priority).</p>

### 3. Individual workshop addons
<p>Mounts an individual addon from the workshop.</p>
<p>Occasionally, the app may error on valid links. Retry the 'Mount' operation a few times or restart the app.</p>
<h2>Mounting settings</h2>
<ul>
    <li><strong>Validate files</strong> - addons with missing files will be skipped</li>
    <li><strong>Check maps automatically</strong> - see "<b>Maps</b>" tab</li>
    <li><strong>Sync with Episodes</strong> - immediately duplicate the addon list in Episode 1 VR and Episode 2 VR when any changes are made</li>
</ul>