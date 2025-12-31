from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, 
                             QPushButton, QTabWidget, QWidget)
from PyQt5.QtCore import Qt
from config import load_config

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_config()
        self.language = self.config.get("language", "en")
        
        if self.language == "ru":
            self.setWindowTitle("Справка")
        else:
            self.setWindowTitle("Help")
            
        self.setMinimumSize(700, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tabs
        self.tabs = QTabWidget()
        
        # Tab names based on language
        if self.language == "ru":
            tab_names = ["Обзор", "Встраивание аддонов", "Управление списком", "Карты", 
                        "Рекомендации и проблемы", "Anniversary Update"]
        else:
            tab_names = ["Overview", "Mounting addons", "List management", "Maps", 
                        "Recommendations and issues", "Anniversary Update"]
        
        # "Overview" tab
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        overview_text = QTextBrowser()
        overview_text.setOpenExternalLinks(True)
        overview_text.setHtml(self.get_overview_html())
        overview_layout.addWidget(overview_text)
        self.tabs.addTab(overview_tab, tab_names[0])
        
        # "Mounting Addons" tab
        adding_tab = QWidget()
        adding_layout = QVBoxLayout(adding_tab)
        adding_text = QTextBrowser()
        adding_text.setOpenExternalLinks(True)
        adding_text.setHtml(self.get_adding_html())
        adding_layout.addWidget(adding_text)
        self.tabs.addTab(adding_tab, tab_names[1])
        
        # "List Management" tab
        management_tab = QWidget()
        management_layout = QVBoxLayout(management_tab)
        management_text = QTextBrowser()
        management_text.setOpenExternalLinks(True)
        management_text.setHtml(self.get_management_html())
        management_layout.addWidget(management_text)
        self.tabs.addTab(management_tab, tab_names[2])
        
        # "Maps and Episodes" tab
        maps_tab = QWidget()
        maps_layout = QVBoxLayout(maps_tab)
        maps_text = QTextBrowser()
        maps_text.setOpenExternalLinks(True)
        maps_text.setHtml(self.get_maps_html())
        maps_layout.addWidget(maps_text)
        self.tabs.addTab(maps_tab, tab_names[3])
        
        # Recommendations and Issues
        recommendations_tab = QWidget()
        recommendations_layout = QVBoxLayout(recommendations_tab)
        recommendations_text = QTextBrowser()
        recommendations_text.setOpenExternalLinks(True)
        recommendations_text.setHtml(self.get_recommendations_html())
        recommendations_layout.addWidget(recommendations_text)
        self.tabs.addTab(recommendations_tab, tab_names[4])

        # Anniversary Update
        anniversary_tab = QWidget()
        anniversary_layout = QVBoxLayout(anniversary_tab)
        anniversary_text = QTextBrowser()
        anniversary_text.setOpenExternalLinks(True)
        anniversary_text.setHtml(self.get_anniversary_html())
        anniversary_layout.addWidget(anniversary_text)
        self.tabs.addTab(anniversary_tab, tab_names[5])
        
        layout.addWidget(self.tabs)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        if self.language == "ru":
            close_btn = QPushButton("Закрыть")
        else:
            close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
    
    def get_overview_html(self):
        if self.language == "ru":
            return """
            <h1>HL2:VR Workshop Extender</h1>
            
            <h2>Назначение программы</h2>
            <p>Эта программа позволяет удобно встраивать аддоны из мастерской Half-Life 2 в Half-Life 2: VR Mod и Эпизоды, также предлагая базовые функции для их менеджмента.
            Работает ТОЛЬКО с мастерской Half-Life 2!</p>
            
            <p><b>(!) Аддоны из мастерской Half-Life 2: VR Mod (или Эпизодов) и аддоны из папки "custom" всегда берут приоритет над аддонами, встроенными через эту программу.</b></p>

            <p>Учтите, что данная программа является лишь удобным набором костылей, поэтому корректная работа любых модов не гарантируется.
            Она лучше всего подходит для простых рескинов, но карты и некоторые моды тоже могут работать (см. вкладки <b>Карты</b> и <b>Рекомендации и проблемы</b>).</p>

            <h2>Основные возможности</h2>
            <ul>
                <li>Встраивание установленных аддонов</li>
                <li>Встраивание аддонов из коллекций мастерской Steam</li>
                <li>Встраивание отдельных аддонов</li>
                <li>Встраивание аддонов в Эпизоды</li>
                <li>Управление порядком загрузки аддонов</li>
                <li>Проверка файлов аддонов на существование</li>
                <li>Поддержание работоспособности аддонов-карт</li>
                <li>Сохранение и загрузка списка аддонов</li>
                <li>Установка контента Anniversary Update</li>
            </ul>

            <p>Для разъяснения по всем функциям обратитесь к следующим вкладкам справки.</p>

            <h2>Краткий принцип работы</h2>
            <p>
            Программа не скачивает, а только встраивает уже скачанные через Steam аддоны. Это происходит следующим образом:
            </p>
            <ol>
                <li>Программа получает ID аддонов либо с их страницы в Steam, либо из workshop.txt (файл списка аддонов, используемый в HL2).</li>
                <li>Использует эти ID для формирования путей к файлам аддонов в папке мастерской Half-Life 2 (*\\steamapps\\workshop\\content\\220).</li>
                <li>Вставляет эти пути в файл gameinfo.txt Half-Life 2 VR между специальными метками, тем самым говоря игре использовать этот контент.</li>
            </ol>

            <p><br><br>В случае возникновения каких-либо проблем или вопросов вы можете оставить issue на github, связаться со мной в Discord (@dzhonnee) или Steam (https://steamcommunity.com/id/dzhonnee/)</p>
            """
        else:
            return """
            <h1>HL2:VR Workshop Extender</h1>
            
            <h2>Program purpose</h2>
            <p>This tool allows you to conveniently mount addons from Half-Life 2's workshop into Half-Life 2: VR Mod and its Episodes, while providing basic management features. 
            Works ONLY with the Half-Life 2 workshop!</p>
            
            <p><b>(!) Addons from Half-Life 2: VR Mod (or Episodes) workshop and addons in the "custom" folder always take priority over addons mounted through this tool.</b></p>

            <p>Please note that this tool is essentially a collection of workarounds, so proper functionality of every mod is not guaranteed. 
            It works best with reskins, but maps and some mods should also work (see <b>Maps</b> and <b>Recommendations and issues</b> tabs).</p>

            <h2>Main features</h2>
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
            """
    
    def get_adding_html(self):
        if self.language == "ru":
            return """
            <h1>Встраивание аддонов</h1>
            
            <h2>Способы встраивания</h2>
            
            <h3>1. Установленные аддоны</h3>
            <p>Встраивает аддоны, на которые вы подписаны и которые присутствуют в списке аддонов в Half-Life 2 с учетом порядка. 
            Учтите, что аддоны появляются в списке аддонов Half-Life 2 только если после подписки вы зайдете в игру, либо если вы подписываетесь с запущенной игрой.
            <br><b>(!)</b> Эта функция не встраивает аддоны-карты, которые отображаются в HL2 как отдельная кампания. 
            Встраивайте их как отдельный аддон или создайте из своих аддонов коллекцию и встройте её.
            <br>P.S. во время загрузки в логах можно заметить, что неоторые аддоны загружаются в неправильном порядке (например, 1/5, 3/5, 5/5, 4/5, 2/5).
            Это нормально, так как происходит многопоточная обработка, итоговый список все равно будет создан в правильном порядке, как в списке HL2.
            </p>

            <h3>2. Коллекции мастерской</h3>
            <p>Встраивает аддоны из коллекции в ОБРАТНОМ порядке, потому что именно так после загрузки коллекции они отображаются в HL2. Создатели коллекций составляют их именно
            с учетом обратного порядка (ниже позиция - выше приоритет).
            </p>
            
            <h3>3. Отдельные аддоны мастерской</h3>
            <p>Встраивает отдельный аддон из мастерской.</p>
            <p>Иногда программа может ругаться на ссылки не смотря на то, что они правильные. Попробуйте еще несколько раз нажать на встраивание или перезапустите программу.</p>
            <h2>Настройки встраивания</h2>
            <ul>
                <li><strong>Проверять наличие файлов</strong> - аддоны с отсутствующими файлами будут пропускаться</li>
                <li><strong>Проверять карты автоматически</strong> - см. вкладку "<b>Карты</b>"</li>
                <li><strong>Синхронизировать с Эпизодами</strong> - сразу дублировать список аддонов в Episode 1 VR и Episode 2 VR при каких-либо изменениях</li>
            </ul>

            
            """
        else:
            return """
            <h1>Mounting addons</h1>
            
            <h2>Mounting methods</h2>
            
            <h3>1. Installed addons</h3>
            <p>Mounts addons you're subscribed to that are present in the Half-Life 2 addon list, maintaining their order. 
            Note that addons only appear in the Half-Life 2 addon list if you enter the game after subscribing, or if you subscribe with the game running.
            <br><b>(!)</b> This function doesn't mount map addons that appear in HL2 as separate campaigns. 
            Mount them as individual addons or create a collection from your addons and mount it.
            <br>P.S. During the loading process, you may notice in the logs that some addons are loaded in the wrong order (e.g., 1/5, 3/5, 5/5, 4/5, 2/5).
            This is normal behavior, as multi-threaded processing is occurring. The final list will still be created in the correct order, matching the HL2 list.
            </p>

            <h3>2. Workshop collections</h3>
            <p>Mounts addons from a collection in REVERSE order because this is exactly how they appear in HL2 after the collection is loaded. 
            Collection creators assemble their collections specifically with reverse order in mind (lower position - higher priority).</p>
            
            <h3>3. Individual workshop addons</h3>
            <p>Mounts an individual addon from the workshop.</p>
            <p>Occasionally, the app may error on valid links. Retry the 'Mount' operation a few times or restart the app.</p>
            <h2>Mounting settings</h2>
            <ul>
                <li><strong>Validate files</strong> - addons with missing files will be skipped</li>
                <li><strong>Check maps automatically</strong> - see "<b>Maps</b>" tab</li>
                <li><strong>Sync with Episodes</strong> - immediately duplicate the addon list in Episode 1 VR and Episode 2 VR when any changes are made</li>
            </ul>

            
            """
    
    def get_management_html(self):
        if self.language == "ru":
            return """
            <h1>Управление списком аддонов</h1>
            
            <h2>Изменение порядка</h2>
            <br><b>(!) Выше позиция - выше приоритет</b>
            <br><br><b>Кликните по аддону, чтобы выбрать его для перемещения.</b>
            <b>Перемещать можно только по одному аддону.</b>
            <ul>
                <li><b>&lt; &gt;</b> - перемещение на одну позицию</li>
                <li><b>|&lt;&lt; &gt;&gt;|</b> - перемещение в начало/конец списка</li>
                <li><b>Удерживайте кнопки для непрерывного перемещения</b></li>
            </ul>
            
            <h2>Флажки</h2>
            <p>Используются для отметки нескольких аддонов. Флажок сверху - отметить все / снять отметки. <br><b>Отметки используются только при удалении аддонов.</b></p>

            <h2>Поиск</h2>
            <p>Поиск аддонов по названию (без учета регистра). Поддерживается поиск по ID. Используйте кнопки со стрелками для перехода между результатами.</p>
            
            <h2>Дополнительные функции</h2>
            <ul>
                <li><b>Обновить список (⟳)</b> - перезагрузить список аддонов (заново прочитать gameinfo.txt)</li>
                <li><b>Обратный порядок аддонов (⇵)</b> - говорит само за себя</li>
                <li><b>Проверить файлы</b> - при наличии аддонов с несуществующими файлами программа предложит удалить их из списка</li>
                <li><b>Проверить карты</b> - см. вкладку "<b>Карты</b>"</li>
                <li><b>Повторить синхронизацию (⟳)</b> - синхронизировать нынешний список с Эпизодами</li>
                <li><b>Сохранить/Загрузить список</b> - сохраняет текущий список аддонов в .txt файл, при загрузке текущий список заменяется</li>
            </ul>
            """
        else:
            return """
            <h1>Addon list management</h1>
            
            <h2>Changing order</h2>
            <br><b>(!) Higher position - higher priority</b>
            <br><br><b>Click on an addon to select it for moving.</b>
            <b>Only one addon can be moved at a time.</b>
            <ul>
                <li><b>&lt; &gt;</b> - move by one position</li>
                <li><b>|&lt;&lt; &gt;&gt;|</b> - move to the top/bottom of the list</li>
                <li><b>Hold buttons for continuous movement</b></li>
            </ul>
            
            <h2>Checkboxes</h2>
            <p>Used to mark multiple addons. Top checkbox - mark all / clear all marks. <br><b>Marks are only used when deleting addons.</b></p>

            <h2>Search</h2>
            <p>Search addons by name (case insensitive). ID search is supported. Use arrow buttons to navigate between results.</p>
            
            <h2>Additional functions</h2>
            <ul>
                <li><b>Refresh list (⟳)</b> - reload the addon list (re-read gameinfo.txt)</li>
                <li><b>Reverse addons order (⇵)</b> - self-explanatory</li>
                <li><b>Check files</b> - if addons with non-existent files are found, the program will offer to remove them from the list</li>
                <li><b>Check maps</b> - see "<b>Maps</b>" tab</li>
                <li><b>Resync (⟳)</b> - synchronize current list with Episodes</li>
                <li><b>Save/Load list</b> - saves current addon list to .txt file, loading will replace the current list</li>
            </ul>
            """
    
    def get_maps_html(self):
        if self.language == "ru":
            return """
            <h1>Карты</h1>
            
            <h2>В чем проблема?</h2>
            <p>Если встраивать аддоны-карты так же как и обычные аддоны, то в VR моде на этих картах не будет части текстур и моделей из-за того, 
            что игра почему-то не может нормально прочитать файлы карт, если они запакованы в .vpk архив, как все обычные аддоны. 
            Проблема решается распаковкой архива и встраиванием этой распакованной папки вместо .vpk файла в gameinfo.txt, что выполняется через функцию проверки.</p>
            
            <h2>Как работает проверка?</h2>
            <p>Программа проверяет страницу аддона в мастерской Steam на наличие тега maps. 
            Аддон помечается меткой MAP и предлагается распаковать этот аддон, после чего, в случае согласия, аддон распаковывается в своей папке и обновляется ссылка в gameinfo.txt.</p>

            <h3>Функции проверки</h3>
            <ul>
                <li><b>Автоматически (флажок)</b> - проверяются только те аддоны, которые в данный момент добавляются</li>
                <li><b>Кнопка "Проверить карты"</b> - проверяются все аддоны в списке</li>
                <li><b>Правой кнопкой мыши → "Проверить карту"</b> - проверка отдельного аддона через контекстное меню</li>
                <br><li><b>Очистить карты</b> - удаление всех распакованных папок, изменение путей в gameinfo.txt обратно на .vpk</li>
            </ul>

            <h2>Ошибка распаковки карты</h2>
            <p>В случае ошибки попробуйте альтернативный способ распаковки:</p>
            <ol>
                <li>Откройте папку программы и зайдите в папку <b>alt_vpk_extractor</b></li>
                <li>Откройте папку проблемного аддона</li>
                <li>Найдите файл <b>workshop_dir.vpk</b></li>
                <li>Перетащите его на файл <b>vpk.exe</b> в ранее открытой папке программы и дождитесь распаковки</li>
                <li>Выполните <b>Проверить карту</b> для этого аддона</li>
            </ol>
            """
        else:
            return """
            <h1>Maps</h1>
            
            <h2>What's the problem?</h2>
            <p>If map addons are mounted like regular addons, then in VR mod these maps will be missing some textures and models because 
            the game for some reason can't properly read map files if they're packed in .vpk archives like all regular addons. 
            The problem is solved by unpacking the archive and mounting this unpacked folder instead of the .vpk file in gameinfo.txt, which is done through the check function.</p>
            
            <h2>How does checking work?</h2>
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
            """

    def get_recommendations_html(self):
        if self.language == "ru":
            return """
            <h2>Рекомендации</h2>
            <ul>
            <li>С модами, представляющими собой простой набор карт с каким-либо минимальным кастомным контентом (материалы, модели), не должно возникать серьезных проблем.
            Проблемы могут быть тогда, когда в моде есть свои ресурсы, скрипты, конфиги и тому подобное, т.е. полноценный мод с кампанией. 
            Вы можете проверить наличие таких папок, открыв папку аддона, если он был распакован. Но в принципе даже так многие моды будут как минимум играбельными.</li>

            <br><li>Если вы собираетесь играть в аддоны-кампании, то <b>запускайте их только через Episode 2 VR</b>, поскольку они могут использовать контент Эпизодов.
            Это обычно не касается карт, которые заменяют оригинальные карты HL2.</li>

            <br><li>Для более корректной работы карт следует установить контент <b>Anniversary Update</b> (см. вкладку).</li>

            <br><li>Не добавляйте больше одного аддона-кампании, чтобы избежать ошибок из-за файловых конфликтов.</li>
            </ul>

            <h2>Проблемы</h2>
            <ul>
            <li>Некоторые аддоны-кампании при заходе в игру будут каждый раз сбрасывать ваши VR настройки и предлагать пройти первоначальную настройку.
            Решается удалением следующего файла в папке аддона: <b>*ID*\\workshop_dir\\cfg\\config.cfg</b></li>

            <br><li>В некоторых аддонах-кампаниях отсутствует фоновая карта для меню, поэтому для навигации в меню придется использовать рабочий стол.</li>

            <br><li>Если в моде не предусмотрено разделение на главы, первую карту придется загружать через консоль.</li>

            <br><li>Если в моде есть какие-то нововведения в интерфейсе, скорее всего они не будут корректно работать (например радио-сообщения в моде Hatch18).</li>

            <br><li>На некоторых картах могут быть сломаны скайбоксы (скайбокс выглядит растянутым).</li>

            <br><li>На некоторых картах может некорректно выглядеть туман (слишком яркий, выделяющийся на фоне неба).</li>

            <br><li>Всегда есть малая вероятность появления ошибки "A.I. Disabled".</li>

            <br><li>Некоторые моды могут вообще не запускаться. Для возможного исправления откройте папку аддона и удалите все файлы кроме папок, если они есть.

            </li>
            </ul>

            <h2>Превышен лимит запросов Steam</h2>
            <p>
            Эта ошибка может возникать при попытке встроить установленные аддоны или проверить карты.
            </p>

<p>Что это значит?</p>

            <ul>
            <li>Steam в данный момент ограничивает запросы к своим серверам из-за высокой нагрузки, вероятно вызванной каким-то событием или временными проблемами Steam.</li>
            <li>Вы временно не можете открывать страницы предметов мастерской. Это ограничение обычно действует всего пару минут. Подождите немного, а затем проверьте, открываются ли страницы предметов.</li>
            <li>Из-за этих ограничений в данный момент у вас не получится встроить установленные аддоны или проверить карты в списке аддонов.</li>
            </ul>

<p>Что делать?</p>
            <ul>
            <li>Убедитесь, что доступ к страницам предметов мастерской восстановлен.</li>
            <li>Отключите автоматическую проверку карт.</li>
            <li>Вам придется самим определять, какие аддоны являются картами, и проверять их правой кнопкой мыши по аддону в таблице.</li>
            <li>Если вы пытались встроить установленные аддоны, используйте коллекции в качестве обходного метода:
            <br>1. Откройте Ваши подписки;
            <br>2. Нажмите «Сохранить в коллекции» и сохраните в новой коллекции;
            <br>3. Откройте коллекцию, измените видимость на «по ссылке» и дождитесь, когда исчезнет плашка «Эта работа ещё не проанализирована...»;
            <br>4. Встройте коллекцию. Убедитесь, что порядок аддонов соответствует списку в HL2.</li>
            
            </ul>

            """
        else:
            return """
            <h2>Recommendations</h2>
            <ul>
            <li>With mods that are simple packs of maps with some minimal custom content (materials, models), there shouldn't be serious problems.
            Problems may occur when the mod has its own resources, scripts, configs, etc., i.e., a full-fledged mod with a campaign. 
            You can check for such folders by opening the addon folder if it was unpacked. But even so, many mods will be at least playable.</li>

            <br><li>If you're going to play campaign addons, <b>launch them only through Episode 2 VR</b>, as they may use Episode content.
            This usually doesn't apply to maps that replace original HL2 maps.</li>

            <br><li>For more correct map functionality, install the <b>Anniversary Update</b> content (see tab).</li>

            <br><li>Don't mount more than one campaign addon to avoid errors due to file conflicts.</li>
            </ul>

            <h2>Issues</h2>
            <ul>
            <li>Some campaign addons will reset your VR settings every time you enter the game and prompt you to go through initial setup.
            Solved by deleting the following file in the addon folder: <b>*ID*\\workshop_dir\\cfg\\config.cfg</b></li>

            <br><li>Some campaign addons lack a background map for the menu, so you'll have to use the desktop for menu navigation.</li>

            <br><li>If the mod doesn't have chapter separation, you'll have to load the first map through the console.</li>

            <br><li>If the mod has some custom interfaces, they likely won't work correctly (e.g., radio messages in Hatch18 mod).</li>

            <br><li>Some maps may have broken skyboxes (skybox looks stretched).</li>

            <br><li>On some maps, fog may look incorrect (too bright, standing out against the sky).</li>

            <br><li>There's always a small chance of "A.I. Disabled" error appearing.</li>

            <br><li>Some mods may not launch at all. To potentially fix this, open the addon's folder and delete all files except folders, if they exist.
            </li>
            </ul>

            <h2>Steam request limit exceeded</h2>
            <p>
            This error may occur when you try to mount installed addons or check maps.
            </p>
<p>What does it mean?</p>

            <ul>
            <li>Steam is currently limiting requests to its servers due to high load, likely caused by an event or Steam just having trouble.</li>
            <li>You temporarily cannot access Workshop item pages. This limitation usually lasts only a couple of minutes. Wait a bit and then check if item pages open.</li>
            <li>Due to these limitations, you currently won't be able to mount installed addons or check maps in your addon list.</li>
            </ul>

<p>What to do?</p>
            <ul>
            <li>Make sure you have regained access to Workshop item pages.</li>
            <li>Disable automatic map checking.</li>
            <li>You'll need to manually identify which addons are maps and check them by right-clicking on an addon in the table.</li>
            <li>If you were trying to mount installed addons, use collections as a workaround:
            <br>1. Open your Subscribed items;
            <br>2. Click 'Save to collection' and save to a new collection;
            <br>3. Open the collection, change visibility to 'Unlisted' and wait until the 'This item is awaiting analysis...' notice disappears;
            <br>4. Mount the collection. Verify that the addon order matches the list in HL2.</li>
            
            </ul>
            
            """

    def get_anniversary_html(self):
        if self.language == "ru":
            return """
            <h1>Anniversary Update</h1>

            <p>Установка Anniversary Update встроит все улучшения из последней версии Half-Life 2 в VR Мод и Эпизоды.
            <br><br>Эта процедура меняет пути к игровому контенту в файлах gameinfo.txt и заменяет некоторые файлы карт и шейдеров для их корректной работы.
            </p>
            
            <h2>Возврат к оригинальной версии</h2>
            <ol>
                <li>Зайдите в папку Half-Life 2 VR/hlvr</li>
                <li>Удалите папки "maps" и "shaders"</li>
                <li>В библиотеке Steam кликните правой кнопкой на Half-Life 2: VR Mod</li>
                <li>Выберите "Свойства" → "Установленные файлы"</li>
                <li>Нажмите "Проверить целостность файлов игры"</li>
                <li>Так же проверьте целостность файлов для Эпизодов VR</li>
            </ol>
            """
        else:
            return """
            <h1>Anniversary Update</h1>

            <p>Installing Anniversary Update will mount all enhancements from the latest Half-Life 2 version into VR Mod and Episodes.
            <br><br>This procedure changes game content paths in gameinfo.txt files and replaces some map and shader files for their correct operation.
            </p>
            
            <h2>Reverting to original version</h2>
            <ol>
                <li>Go to the Half-Life 2 VR/hlvr folder</li>
                <li>Delete the "maps" and "shaders" folders</li>
                <li>In Steam library, right-click on Half-Life 2: VR Mod</li>
                <li>Select "Properties" → "Installed Files"</li>
                <li>Click "Verify integrity of game files"</li>
                <li>Also verify file integrity for VR Episodes</li>
            </ol>
            """