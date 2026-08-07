# Mounting addons

## Mounting methods

### 1. Installed addons
<p>Mounts addons you're subscribed to that are present in the Half-Life 2 addon list, maintaining their order. 
Note that addons only appear in the Half-Life 2 addon list if you enter the game after subscribing, or if you subscribe with the game running.
<br><b>(!)</b> This function doesn't mount map addons that appear in HL2 as separate campaigns. 
Mount them as individual addons or create a collection from your addons and mount it.
</p>

### 2. Workshop collections
<p>Mounts addons from a collection in REVERSE order because this is exactly how they appear in HL2 after the collection is loaded. 
Collection creators should assemble their collections specifically with reverse order in mind (lower position - higher priority).</p>

### 3. Individual workshop addons
<p>Mounts an individual addon from the workshop.</p>
<p>Occasionally, the app may error on valid links. Retry the 'Mount' operation a few times or restart the app.</p>

### 4. External (non-workshop) mods
<p>Since v1.1 you can mount mods downloaded from GameBanana or any other source by placing them in any convenient folder and scanning it with the tool.</p>

<p><b>Requirements:</b></p>
<ul>
    <li>The folder <b>must not</b> be HL2VR's <code>custom</code> folder (to avoid conflicts)</li>
    <li>The folder should <b>not be moved</b> after mounting</li>
    <li>Mods must be in <b>VPK format</b> or in a <b>folder format</b></li>
</ul>

<p><b>Folder structure example:</b></p>
<pre>
your_mods_folder/
├── mod_name_1/
│   ├── materials/
│   ├── models/
│   ├── sounds/
│   └── (other Source Engine folders)
├── mod_name_2.vpk
└── mod_name_3/
    ├── maps/
    └── materials/
</pre>

<p><b>Important:</b></p>
<ul>
    <li>The tool will filter out mods with incorrect structure and warn you</li>
    <li>For folder-based mods, the tool will automatically remove files that conflict with VR Mod (configs, shaders, gameinfos, etc.). These files are often presented in maps/campaign mods, so make sure they are not VPK.</li>
</ul>

## Mounting settings
<ul>
    <li><strong>Validate files</strong> - addons with missing files will be skipped</li>
    <li><strong>Check maps automatically</strong> - see "<b>Maps</b>" tab</li>
    <li><strong>Sync with Episodes</strong> - immediately duplicate the addon list in Episode 1 VR and Episode 2 VR when any changes are made</li>
</ul>