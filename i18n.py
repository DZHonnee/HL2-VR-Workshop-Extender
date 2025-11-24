from PyQt5.QtCore import QObject, pyqtSignal
from logger import log

class Translator(QObject):
    language_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.current_language = 'en'
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        try:
            self.translations['ru'] = {
                "Language" : "Язык",
                "Preparing data...": "Подготавливаем данные...",
                "Mounting addons...": "Встраиваем аддоны...",
                "Collection successfully processed!": "Коллекция успешно обработана!",
                "Addon successfully mounted!": "Аддон успешно встроен!",
                "Preparing data...": "Подготавливаем данные...",
                "Mounting addons...": "Встраиваем аддоны...",
                "Installed addons successfully processed!": "Установленные аддоны успешно обработаны!",


"Error": "Ошибка",
"Extraction cancelled": "Распаковка отменена",
"Mounting confirmation": "Подтверждение встраивания",
"Success": "Успех",

"Successfully extracted maps:": "Успешно распакованные карты:",
"Extraction errors:": "Ошибки при распаковке:",
"Maps to extract:": "Карты для распаковки:",
"Already extracted maps:": "Уже распакованные карты:",
"Addons to add:": "Добавляемые аддоны:",
"Addons to remove:": "Удаляемые аддоны:",
"Missing addons:": "Отсутствующие аддоны:",
"Duplicates (skipped):": "Дубликаты (пропущены):",
"Missing addons (skipped):": "Отсутствующие аддоны (пропущены):",
"Failed to get information:": "Не удалось получить информацию:",
"Yes": "Да",
"No": "Нет",
"Remove": "Удалить",
"Cancel": "Отмена",
"Remove missing": "Удалить отсутствующие",
"Extract maps": "Распаковать карты",
"Skip": "Пропустить",
"OK": "ОК",
"No maps to extract": "Нет карт для распаковки",


"Half-Life 2 VR Mod folder:": "Папка Half-Life 2 VR Mod",
"Browse": "Обзор",
"Select Half-Life 2 VR folder": "Выберите папку Half-Life 2 VR",
"Half-Life 2 folder:": "Папка Half-Life 2:",
"Select Half-Life 2 folder": "Выберите папку Half-Life 2",
"Mount installed addons": "Встроить установленные аддоны",
"Steam Workshop collection URL:": "Ссылка на коллекцию мастерской Steam:",
"Mount collection": "Встроить коллекцию",
"Addon URL:": "Ссылка на аддон:",
"Mount addon": "Встроить аддон",
"Validate files": "Проверять наличие файлов",
"Check maps automatically": "Проверять карты автоматически",
"Sync with Episodes": "Синхронизировать с Эпизодами",
"Checking Episodes...": "Проверка Эпизодов...",
"Mount Anniversary Update content": "Встроить контент Anniversary update",
"Help": "Справка",
"Search:": "Поиск:",
"Resync": "Повторить синхронизацию",
"Name": "Название",
"Link": "Ссылка", 
"Folder": "Папка",
"Refresh addons list": "Обновить список аддонов",


"Save list": "Сохранить список",
"Load list": "Загрузить список",
"Check files": "Проверить файлы",
"Check maps": "Проверить карты",
"Clear maps": "Очистить карты",
"Remove selected": "Удалить выбранные",
"Remove all": "Удалить все",



"To top": "В самый верх",
"Up (hold for continuous movement)": "Вверх (удерживайте для быстрого перемещения)",
"Down (hold for continuous movement)": "Вниз (удерживайте для быстрого перемещения)",
"To bottom": "В самый низ",


"Warning": "Внимание",
"End marker of addons block (//mounted_addons_end) found, but start marker is missing!\n\nRemove the addons list with marker from gameinfo.txt, or add //mounted_addons_start to the beginning of the list.": "Обнаружена метка конца блока аддонов (//mounted_addons_end), но отсутствует метка начала!\n\nУдалите из gameinfo.txt список аддонов с меткой, либо добавьте //mounted_addons_start в начало списка.",
"Start marker of addons block (//mounted_addons_start) found, but end marker is missing!\n\nRemove the addons list with marker from gameinfo.txt, or add //mounted_addons_end to the end of addons list in gameinfo.txt.": "Обнаружена метка начала блока аддонов (//mounted_addons_start), но отсутствует метка конца!\n\nУдалите из gameinfo.txt список аддонов с меткой, либо добавьте //mounted_addons_end в конец списка аддонов в gameinfo.txt.",
"Error loading addons list:\n": "Ошибка при загрузке списка аддонов:\n",


"Information": "Информация",
"No addons to save.": "Нет аддонов для сохранения.",
"Save addons list": "Сохранить список аддонов",
"Addons list successfully saved!": "Список аддонов успешно сохранен!",
"Failed to save file:\n": "Не удалось сохранить файл:\n",



"Specify Half-Life 2 VR path": "Укажите путь к Half-Life 2 VR",
"Load addons list": "Загрузить список аддонов",
"File is not a valid addons list save.": "Файл не является корректным сохранением списка аддонов.",
"Confirmation": "Подтверждение",
"Current addons list will be completely replaced. Continue?": "Текущий список аддонов будет полностью заменен. Продолжить?",
"gameinfo.txt not found": "gameinfo.txt не найден",
"End marker of addons block (//mounted_addons_end) found, but start marker is missing!\n\nRemove the addons list with marker from gameinfo.txt, or add //mounted_addons_start to the beginning of the list.": "Обнаружена метка конца блока аддонов (//mounted_addons_end), но отсутствует метка начала!\n\nУдалите из gameinfo.txt список аддонов с меткой, либо добавьте //mounted_addons_start в начало списка.",
"Start marker of addons block (//mounted_addons_start) found, but end marker is missing!\n\nRemove the addons list with marker from gameinfo.txt, or add //mounted_addons_end to the end of addons list in gameinfo.txt.": "Обнаружена метка начала блока аддонов (//mounted_addons_start), но отсутствует метка конца!\n\nУдалите из gameinfo.txt список аддонов с меткой, либо добавьте //mounted_addons_end в конец списка аддонов в gameinfo.txt.",
"Failed to add markers to gameinfo.txt: ": "Не удалось добавить метки в gameinfo.txt: ",
"Failed to find addons block markers in gameinfo.txt": "Не удалось найти метки блока аддонов в gameinfo.txt",
"Warning": "Предупреждение",
"List loaded, but failed to sync with episodes: ": "Список загружен, но не удалось синхронизировать с эпизодами: ",
"Addons list successfully loaded!": "Список аддонов успешно загружен!",
"Failed to load addons list:\n": "Не удалось загрузить список аддонов:\n",


"Restart the application to change the language":"Перезапустите приложение для смены языка",
"Language changed":"Язык изменен",


"Episodes not installed": "Эпизоды не установлены",
"Both Episodes installed": "Оба Эпизода установлены",
"Only Episode 1 installed": "Установлен только Эпизод 1",
"Only Episode 2 installed": "Установлен только Эпизод 2",

"Saving addons list to file: ": "Сохранение списка аддонов в файл: ",
"Loading addons list from file: ": "Загрузка списка аддонов из файла: ",
"Addons list successfully loaded from file": "Список аддонов успешно загружен из файла",


"List of {} addons successfully saved": "Список {} аддонов успешно сохранен",
"Error saving addons list: ": "Ошибка при сохранении списка аддонов: ",
"Error loading addons list: ": "Ошибка при загрузке списка аддонов: ",


"Preparing data...": "Подготовка данных...",


"collection": "коллекцию",
"addon": "аддон",
"Enter Steam Workshop URL for {}": "Введите ссылку на {} мастерской Steam",
"Preparing data...": "Подготовка данных...",


"❌ Error preparing data": "❌ Ошибка при подготовке данных",
"Error preparing data: ": "Ошибка подготовки данных: ",
"missing in workshop folder": "отсутствуют в папке мастерской",
"All addons missing in workshop folder": "Все аддоны отсутствуют в папке мастерской",
"All addons already mounted (duplicates)": "Все аддоны уже встроены (дубликаты)",
"Addon Mount Confirmation": "Подтверждение встраивания",
"Will be mounted addon:\n\n{}": "Будет встроен аддон:\n\n{}",
"Operation cancelled": "Операция отменена",
"Addon mounting cancelled by user": "Встраивание аддона отменено пользователем",
"{} addons will be mounted": "Будет встроено {} аддонов",
"Collection mounting cancelled by user": "Встраивание коллекции отменено пользователем",


"Mounting addons...": "Выполняем встраивание...",
"collection": "коллекции",
"addon": "аддона",
"Starting {} mounting execution: {} addons": "Запуск выполнения встраивания {}: {} аддонов",



"❌ Error preparing data": "❌ Ошибка при подготовке данных",
"Error preparing data from workshop.txt: ": "Ошибка подготовки данных из workshop.txt: ",
"No addons to mount from workshop.txt": "Нет аддонов для добавления из workshop.txt",
"{} addons will be mounted": "Будет добавлено {} аддонов",
"Addon mount confirmation": "Подтверждение добавления",
"Operation cancelled": "Операция отменена",
"Addons mounting from workshop.txt cancelled by user": "Добавление аддонов из workshop.txt отменено пользователем",
"Starting addons mounting execution from workshop.txt": "Запуск выполнения встраивания аддонов из workshop.txt",
"Mounting addons...": "Выполняем встраивание...",



"single addon": "одиночного аддона",
"collection": "коллекции",
"addons from workshop.txt": "аддонов из workshop.txt",
"addons": "аддонов",
"Mounting of {} completed": "Встраивание {} завершено",
"Added {} addons": "Добавлено {} аддонов",
"{} addons": "{} аддонов",
"addons: {}": "аддонов: {}",
"Failed to determine number of new addons for check": "Не удалось определить количество новых аддонов для проверки",
"Auto map check disabled in settings": "Автопроверка карт отключена в настройках",
"❌ Error adding addons": "❌ Ошибка при добавлении аддонов",
"Error during mounting execution: ": "Ошибка при выполнении встраивания: ",




"First select Half-Life 2 VR folder": "Сначала выберите папку Half-Life 2 VR",
"Information": "Информация",
"Check addons to remove.": "Отметьте аддоны для удаления.",
"Preparing removal of {} selected addons": "Подготовка удаления {} выбранных аддонов",
"Remove addons confirmation": "Подтверждение удаления",
"Do you really want to remove the following {} addons?": "Вы действительно хотите удалить следующие {} аддонов?",
"Addons removal cancelled by user": "Удаление аддонов отменено пользователем",
"Addons successfully removed!": "Аддоны успешно удалены!",
"\nWarning: ": "\nПредупреждение: ",
"Successfully removed {} addons": "Успешно удалено {} аддонов",
"Error removing addons: ": "Ошибка при удалении аддонов: ",


"First select Half-Life 2 VR folder": "Сначала выберите папку Half-Life 2 VR",
"Information": "Информация",
"No addons to remove.": "Нет аддонов для удаления.",
"Preparing removal of all {} addons": "Подготовка удаления всех {} аддонов",
"Remove all confirmation": "Подтверждение удаления",
"Do you really want to remove ALL {} addons?": "Вы действительно хотите удалить ВСЕ {} аддонов?",
"Ready": "Готов к работе",
"Removal of all addons cancelled by user": "Удаление всех аддонов отменено пользователем",
"All addons successfully removed!": "Все аддоны успешно удалены!",
"\nWarning: ": "\nПредупреждение: ",
"Successfully removed all {} addons": "Успешно удалены все {} аддонов",

"Error removing all addons: ": "Ошибка при удалении всех аддонов: ",



"First select Half-Life 2 VR folder": "Сначала выберите папку Half-Life 2 VR",
"Information": "Информация",
"No addons to check.": "Нет аддонов для проверки.",
"Checking files...": "Проверка файлов...",
"All addon files are present": "Все файлы аддонов присутствуют",
"Files checked": "Файлы проверены",
"All addons are installed.": "Все аддоны установлены.",
"Found {} addons with missing files": "Обнаружено {} аддонов с отсутствующими файлами",
"Missing Addons Found": "Обнаружены отсутствующие аддоны",
"Found {} addons with missing files. Remove them from the list?": "Обнаружено {} аддонов с отсутствующими файлами. Удалить их из списка?",
"Ready": "Готов к работе",
"Removal of missing addons cancelled by user": "Удаление отсутствующих аддонов отменено пользователем",
"Addons with missing files removed!": "Аддоны с отсутствующими файлами удалены!",
"\nWarning: ": "\nПредупреждение: ",
"Removed {} addons with missing files": "Удалено {} аддонов с отсутствующими файлами",
"Error removing missing addons: ": "Ошибка при удалении отсутствующих аддонов: ",



"Select Half-Life 2 VR folder": "Выберите папку Half-Life 2 VR",
"Information": "Информация",
"No addons to check.": "Нет аддонов для проверки.",
"Checking map for addon: {}": "Проверка карты для аддона: {}",
"Auto map check for {} new addons": "Автопроверка карт для {} новых аддонов",
"Manual map check for {} addons": "Ручная проверка карт для {} аддонов",
"Checking addons for maps...": "Проверка аддонов на карты...",
"Cancel": "Отмена",
"Map check": "Проверка карт",
"Error checking addon {}: {}": "Ошибка при проверке аддона {}: {}",
"Checking addon {} of {}: {}": "Проверка аддона {} из {}: {}",
"Map check cancelled by user": "Проверка карт отменена пользователем",
"Map found: {}": "Обнаружена карта: {}",
"Error processing result for {}: {}": "Ошибка при обработке результата для {}: {}",
"Check completed: {} maps, {} require extraction": "Проверка завершена: {} карт, {} требуют распаковки",


"New map addons found": "Найдены новые аддоны-карты",
"Check completed": "Проверка завершена",
"Addon '{}' is not a map": "Аддон '{}' не является картой",
"Check result": "Результат проверки",
"Addon '{}' is not a map.": "Аддон '{}' не является картой.",
"Map found": "Карта обнаружена",
"Manual check: maps not found": "Ручная проверка: карты не найдены",
"Map check result": "Результат проверки карт",



"Found {} map addons:\n• {} require extraction\n• {} already extracted": "Найдено {} аддонов-карт:\n• {} требуют распаковки\n• {} уже распакованы",
"Found {} map addons that require extraction.": "Найдено {} аддонов-карт, которые требуют распаковки.",
"All {} map addons are already extracted.": "Все {} аддонов-карт уже распакованы.",
"Map addons not found.": "Аддоны-карты не найдены.",
"Addon '{}' is a map but not extracted.": "Аддон '{}' является картой, но не распакован.",
"Starting extraction of {} maps": "Запуск распаковки {} карт",
"Preparing for extraction...": "Подготовка к распаковке...",
"Cancel": "Отмена",
"Map extraction": "Распаковка карт",
"Extracting map: {}": "Распаковка карты: {}",
"Extracting {} maps...": "Распаковка {} карт...",
"Map extraction not required or cancelled by user": "Распаковка карт не требуется или отменена пользователем",



"Map paths and titles updated in gameinfo.txt": "Пути и названия карт обновлены в gameinfo.txt",
"Error updating map paths: ": "Ошибка при обновлении путей карт: ",



"Order updated, but: {}": "Порядок обновлен, но: {}",
"Order saved, but episode sync failed: {}": "Порядок сохранен, но синхронизация с эпизодами не удалась: {}",
"Error saving addons order: ": "Ошибка при сохранении порядка аддонов: ",
"Error saving order: {}": "Ошибка при сохранении порядка: {}",



"Open in Steam": "Открыть в Steam",
"Open folder": "Открыть папку",
"Loaded {} addons": "Загружено {} аддонов",
"Addons table updated": "Таблица аддонов обновлена",



"Uncheck all": "Снять все галочки",


"{} addons for query '{}'": "{} аддонов по запросу '{}'",
"No addons found for query '{}'": "Аддоны по запросу '{}' не найдены",
"Loaded {} addons": "Загружено {} аддонов",


"Previous result": "Предыдущий результат",
"Next result": "Следующий результат",


"Information": "Информация",
"First enable sync with Episodes.": "Сначала включите синхронизацию с Эпизодами.",
"First select Half-Life 2 VR folder": "Сначала выберите папку Half-Life 2 VR",
"No addons to sync.": "Нет аддонов для синхронизации.",
"Manual sync with episodes: {} addons": "Ручная синхронизация с эпизодами: {} аддонов",
"Error syncing with episodes: ": "Ошибка синхронизации с эпизодами: ",



"Sync with episodes disabled": "Синхронизация с эпизодами отключена",
"Half-Life 2 VR path not specified": "Не указан путь к Half-Life 2 VR",
"Episodes not installed": "Эпизоды не установлены",
"Syncing with Episodes...": "Синхронизация с Эпизодами...",
"{}: End marker of addons block (//mounted_addons_end) found, but start marker is missing!\n\nRemove the addons list with marker from gameinfo.txt, or add //mounted_addons_start to the beginning of the list.": "{}: Обнаружена метка конца блока аддонов (//mounted_addons_end), но отсутствует метка начала!\n\nУдалите из gameinfo.txt список аддонов с меткой, либо добавьте //mounted_addons_start в начало списка.",
"{}: Start marker of addons block (//mounted_addons_start) found, but end marker is missing!\n\nRemove the addons list with marker from gameinfo.txt, or add //mounted_addons_end to the end of addons list in gameinfo.txt.": "{}: Обнаружена метка начала блока аддонов (//mounted_addons_start), но отсутствует метка конца!\n\nУдалите из gameinfo.txt список аддонов с меткой, либо добавьте //mounted_addons_end в конец списка аддонов в gameinfo.txt.",
"Failed to add markers to {}: {}": "Не удалось добавить метки в {}: {}",
"Error syncing with {}: {}": "Ошибка синхронизации с {}: {}",
"Sync completed: {} episodes updated": "Синхронизация завершена: {} эпизодов обновлено",
"Synced with Episodes": "Синхронизировано с Эпизодами",
"Error syncing with episodes: ": "Ошибка синхронизации с эпизодами: ",
"Error syncing with episodes: {}": "Ошибка синхронизации с эпизодами: {}",


"First specify paths to Half-Life 2 VR and Half-Life 2": "Сначала укажите пути к Half-Life 2 VR и Half-Life 2",
"Warning": "Внимание",
"This procedure will install Anniversary Update content into Half-Life 2: VR Mod and Episodes.\n\n⚠️ WARNING:\n• Current addons list will be cleared\n• Some game files will be modified\n• Current game saves will stop working\n• Instructions to return to original version are in Help\n\nContinue?": "Эта процедура установит контент Anniversary Update в Half-Life 2: VR Mod и Эпизоды.\n\n⚠️ ВНИМАНИЕ:\n• Текущий список аддонов будет очищен\n• Будут изменены некоторые файлы игры\n• Текущие сохранения игры перестанут работать\n• Инструкция для возврата к оригинальной версии находится в Справке\n\nПродолжить?",
"Operation cancelled": "Операция отменена",
"Anniversary Update installation cancelled by user": "Установка Anniversary Update отменена пользователем",
"Installing anniversary update content...": "Устанавливаем контент юбилейного обновления...",
"Error installing Anniversary Update: ": "Ошибка при установке Anniversary Update: ",
"❌ Error during installation": "❌ Ошибка при установке",
"Error importing anniversary_update module: ": "Ошибка импорта модуля anniversary_update: ",
"Failed to load anniversary_update module: {}": "Не удалось загрузить модуль anniversary_update: {}",
"Unexpected error during Anniversary Update installation: ": "Непредвиденная ошибка при установке Anniversary Update: ",
"An unexpected error occurred: {}": "Произошла непредвиденная ошибка: {}",

"Unknown": "Неизвестно",

"Addon folder not found:\n{}": "Папка аддона не найдена:\n{}",
"Failed to open addon folder:\n{}": "Не удалось открыть папку аддона:\n{}",


"First select Half-Life 2 VR and Half-Life 2 folders": "Сначала выберите папки Half-Life 2 VR и Half-Life 2",
"Clear Confirmation": "Подтверждение очистки",
"This action will delete all extracted map addon folders.\n\nContinue?": "Это действие удалит все распакованные папки аддонов-карт.\n\nПродолжить?",
"Extracted maps clearing cancelled by user": "Очистка распакованных карт отменена пользователем",
"Starting extracted maps clearing...": "Запуск очистки распакованных карт...",
"Failed to find workshop folder": "Не удалось найти папку мастерской",
"gameinfo.txt not found": "Не найден gameinfo.txt",
"Maps cleared!\n{}": "Карты очищены!\n{}",
"Episode sync failed: {}": "Синхронизация с эпизодами не удалась: {}",
"\nWarning: {}": "\nПредупреждение: {}",
"Error clearing maps: ": "Ошибка при очистке карт: ",
"Unexpected error clearing maps: ": "Непредвиденная ошибка при очистке карт: ",
"An unexpected error occurred:\n{}": "Произошла непредвиденная ошибка:\n{}",

"Map {}/{}: {}": "Карта {}/{}: {}",

"Map extraction cancelled by user": "Распаковка карт отменена пользователем",
"General error during map extraction: {}": "Общая ошибка при распаковке карт: {}",
"Extraction Error": "Ошибка распаковки",
"Gameinfo.txt updated with new map paths": "Gameinfo.txt обновлен с новыми путями карт",
"Extraction completed: {} successful, {} failed, total maps: {}": "Распаковка завершена: {} успешно, {} с ошибками, всего карт: {}",
"Successfully extracted {} maps": "Успешно распаковано {} карт",
"Extraction completed": "Распаковка завершена",
"Successful: {} maps\nFailed: {} maps": "Успешно: {} карт\nС ошибками: {} карт",
"Extraction completed with errors": "Распаковка завершена с ошибками",
"Failed to extract {} maps, see Help (Maps tab)": "Не удалось распаковать {} карт, обратитесь к Справке (вкладка 'Карты')",
"Extraction completed. No maps to process.": "Распаковка завершена. Нет карт для обработки.",



"Check map": "Проверить карту",


"Failed to load help module: {}": "Не удалось загрузить модуль справки: {}",


"gameinfo.txt file not found at path: {}": "Файл gameinfo.txt не найден по пути: {}",
"Addon markers not found, searching in entire SearchPaths block": "Метки аддонов не найдены, поиск во всем блоке SearchPaths",
"SearchPaths block not found in gameinfo.txt": "Блок SearchPaths не найден в gameinfo.txt",
"Error reading gameinfo.txt: {}": "Ошибка при чтении gameinfo.txt: {}",


"Removing addons from gameinfo.txt...": "Удаление аддонов из gameinfo.txt...",
"Successfully removed {} addons": "Успешно удалено {} аддонов",
"Removed {} addons": "Удалено {} аддонов",


"Filtering duplicates": "Фильтрация дубликатов",



"Essential VR files prioritized via custom folder": "Важные VR файлы приоритезированы через папку custom",


"workshop.txt not found.": "workshop.txt не найден.",
"Installed addons not found.": "Установленные аддоны не найдены.",
"Read {} addons from workshop.txt": "Прочитано {} аддонов из workshop.txt",

"Found {} missing addon files": "Найдено {} отсутствующих файлов аддонов",


"Preparing addons from collection": "Подготовка аддонов из коллекции",
"Failed to find addons in collection.": "Не удалось найти аддоны в коллекции.",
"All addons from collection already added.": "Все аддоны из коллекции уже добавлены.",
"Failed to find addons.": "Не удалось найти аддоны.",
"Addon files missing.": "Файлы аддонов отсутствуют.",
"Prepared {} addons for mounting": "Подготовлено {} аддонов для встраивания",



"Preparing single addon": "Подготовка одиночного аддона",
"Failed to get addon information.": "Не удалось получить информацию об аддоне.",
"Addon '{}' already added.": "Аддон '{}' уже добавлен.",
"Addon file '{}' not found.": "Не найден файл аддона '{}'.",
"Addon '{}' prepared for mounting": "Аддон '{}' подготовлен для встраивания",



"Starting preparation of addons from workshop.txt": "Начало подготовки аддонов из workshop.txt",
"Installed addons not found.": "Установленные аддоны не найдены.",
"Loaded ({}/{}): {}": "Загружен ({}/{}): {}",
"✗ Failed to load ({}/{}): ID {}": "✗ Не удалось загрузить ({}/{}): ID {}",
"✗ Error loading ({}/{}): ID {} - {}": "✗ Ошибка при загрузке ({}/{}): ID {} - {}",
"✗ Unexpected error ({}/{}): ID {} - {}": "✗ Непредвиденная ошибка ({}/{}): ID {} - {}",
"Failed to get information about installed addons.": "Не удалось получить информацию об установленных аддонах.",
"Successfully processed {} out of {} addons": "Успешно обработано {} из {} аддонов",
"All addons already added.": "Все аддоны уже добавлены.",
"Failed to find addons to add.": "Не удалось найти аддоны для добавления.",
"Checking addon files existence": "Проверка наличия файлов аддонов",
"Addon files missing.": "Файлы аддонов отсутствуют.",
"Prepared {} addons from workshop.txt": "Подготовлено {} аддонов из workshop.txt",



"VPK file not found: {}": "VPK файл не найден: {}",
"Folder already exists and not empty": "Папка уже существует и не пустая",
"VPK file is empty": "VPK файл пустой",
"Starting map extraction: ({} files)": "Начало распаковки карты: ({} файлов)",
"Extraction cancelled": "Распаковка отменена",
"Error extracting {}: {}": "Ошибка при извлечении {}: {}",
"Map extracted: {}/{} files": "Карта распакована: {}/{} файлов",
"Successfully extracted {} files": "Успешно распаковано {} файлов",
"Error extracting map: {}": "Ошибка при распаковке карты: {}",
"Error extracting map: {}. For possible solution see Help (Maps tab).": "Ошибка при распаковке карты: {}. Для возможного решения обратитесь к Справке (вкладка 'Карты').",


"Checking maps: {} addons to process": "Проверка карт: {} аддонов для обработки",
"Maps found: {}": "Найдено карт: {}",
"Checking addon: {}": "Проверка аддона: {}",
"{}: {}": "{}: {}",
"cancelled": "отменена",
"VPK file and non-empty extraction folder not found": "Не найден VPK файл и непустая папка распаковки",
" (VPK: {})": " (VPK: {})",
"Map check completed: {} extracted, {} errors": "Проверка карт завершена: {} распаковано, {} ошибок",



"Clearing extracted maps...": "Очистка распакованных карт...",
"Clearing completed: {} folders deleted, {} paths updated": "Очистка завершена: удалено {} папок, обновлено {} путей",
"Deleted folders: {}": "Удалено папок: {}",



"Game folders not found": "Папки игр не найдены",



"hlvr folder not found, skipping folder copy": "Папка hlvr не найдена, пропускаем копирование папок",


"Episode folders not found": "Папки эпизодов не найдены",


"Starting Anniversary Update installation": "Начало установки Anniversary Update",
"Changes made to files and folders": "Внесены изменения в файлы и папки",
"gameinfo.txt updated": "gameinfo.txt обновлен",
"Anniversary Update successfully installed": "Anniversary Update успешно установлен",
"Anniversary update content installed!": "Контент юбилейного обновления установлен!",


"Updating gameinfo.txt...": "Обновление gameinfo.txt...",
"Missing start marker of addons block! Add //mounted_addons_start to the beginning of addons list in gameinfo.txt.": "Отсутствует метка начала блока аддонов! Добавьте //mounted_addons_start в начало списка аддонов в gameinfo.txt.",
"Missing end marker of addons block! Add //mounted_addons_end to the end of addons list in gameinfo.txt.": "Отсутствует метка конца блока аддонов! Добавьте //mounted_addons_end в конец списка аддонов в gameinfo.txt.",
"Failed to add markers: {}": "Не удалось добавить метки: {}",
"Failed to find addons block markers.": "Не удалось найти метки блока аддонов.",
"Gameinfo.txt updated: {} new addons": "Gameinfo.txt обновлен: {} новых аддонов",
"Added addons: {}": "Добавлено аддонов: {}",


"Addons block markers corrupted.": "Метки блока аддонов повреждены.",
"Failed to find addons block markers.": "Не удалось найти метки блока аддонов.",
"Addons order updated": "Порядок аддонов обновлен",



"Select Half-Life 2 VR folder": "Выберите папку Half-Life 2 VR",
"Select Half-Life 2 folder": "Выберите папку Half-Life 2",
"Wrong path selected for Half-Life 2 VR folder": "Выбран неправильный путь к папке Half-Life 2 VR",
"Wrong path selected for Half-Life 2 folder": "Выбран неправильный путь к папке Half-Life 2",
"gameinfo.txt not found, check file integrity": "gameinfo.txt не найден, проверьте целостность файлов",
"Failed to find workshop folder": "Не удалось найти папку мастерской",



"Getting addons from collection: {}": "Получение аддонов из коллекции: {}",
"Unknown title": "Неизвестное название",
"Got {} addons from collection": "Получено {} аддонов из коллекции",



"Enter URL": "Введите ссылку",
"Invalid URL": "Некорректная ссылка",
"Failed to determine page": "Не удалось определить страницу",
"Page is not a collection": "Страница не является коллекцией",
"Page is not an addon": "Страница не является аддоном",


"gameinfo.txt is corrupted, addons cannot be mounted.": "gameinfo.txt поврежден, аддоны не могут быть встроены.",
"Addon markers added to gameinfo.txt": "Метки аддонов добавлены в gameinfo.txt",


"Copying essential VR files to custom (hlvr)": "Копирование важных VR файлов в custom (hlvr)",
"Copying essential VR files to custom (episodicvr)": "Копирование важных VR файлов в custom (episodicvr)", 
"Copying essential VR files to custom (ep2vr)": "Копирование важных VR файлов в custom (ep2vr)",
"Essential VR files prioritized via custom folder": "Важные VR файлы приоритезированы через папку custom",

            }
            
        except Exception as e:
            log.error(f"Error loading translations: {e}")
            self.translations = {'ru': {}}
    
    def set_language(self, language):
        if language in ['en', 'ru'] and language != self.current_language:
            self.current_language = language
            log.info(f"Language changed to: {language}")
            self.language_changed.emit()
    
    def translate(self, text):
        if self.current_language == 'en':
            return text
        
        return self.translations.get(self.current_language, {}).get(text, text)
    
    def get_available_languages(self):
        return [
            ('en', 'English'),
            ('ru', 'Русский')
        ]

translator = Translator()

def tr(text):
    return translator.translate(text)