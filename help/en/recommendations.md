<h2>Recommendations</h2>
<ul>
<li><b>(!) Launch campaign addons only through Episode 2 VR</b>, as they may use Episode content.
This usually doesn't apply to maps that replace original HL2 maps.</li>
  
<li>With mods that are simple packs of maps with some minimal custom content (materials, models), there shouldn't be serious problems.
Problems may occur when the mod has its own resources, scripts, configs, etc., i.e., a full-fledged mod with a campaign. 
You can check for such folders by opening the addon folder if it was unpacked. But even so, most mods will be playable to some extent.</li>

<li>For more correct map functionality, install the <b>Anniversary Update</b> content (see tab).</li>

<li>Don't mount more than one campaign addon to avoid errors due to file conflicts. Otherwise just place the mod that you currently play on top.</li>
</ul>

<h2>Issues</h2>
<ul>
<li>Some mods lack a background map for the menu, so you'll have to use the desktop for menu navigation.</li>

<li>If the mod doesn't have chapter separation, you'll have to load the first map through the console. Just type "map" in the console and your custom maps should appear under the text field.</li>

<li>If the mod has some custom interfaces, they likely won't work correctly (e.g., radio messages in Hatch18 or MINERVA mods).</li>

<li>Some maps may have broken skyboxes (skybox looks stretched).</li>

<li>On some maps, fog may look incorrect (too bright, standing out against the sky).</li>

<li>There's always a <i>small</i> chance of "A.I. Disabled" error appearing.</li>

<li>Some mods may not launch at all. The program already deletes files that commonly cause this problem, but if it still happens then try to open the addon's folder and delete all files <b>except folders</b> (materials, models, scripts, etc.), if they exist.
</li>
</ul>

<h2>Steam request limit exceeded (error 429)</h2>
<p>
This error may occur when you try to mount a bunch of addons that are unlisted on Steam. You will see them in the log section if they are encountered during the mounting process. They use an old HTTP request method that Steam doesn't like, because unlisted addons are, for some reason, not available through the Steam API.
</p>
<p><b>This means:</b></p>
<ul>
<li>Steam is currently limiting your HTTP requests to the workshop due to a protection mechanism.</li>
<li>You may temporarily lose access to Workshop item pages. This usually lasts only a couple of minutes — wait a bit and then check whether the item pages open.</li>
<li>Wait a couple of minutes before trying mounting again.</li>
</ul>


