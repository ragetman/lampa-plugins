#!/usr/bin/env python3
# myshows-patch.py
# Применяет наши изменения к оригинальному myshows.js (myshows/myshows-temp.js)
# Результат записывается в n-myshows.js
#
# СТРУКТУРА ПАТЧЕЙ:
# Патч 1-4 — подборки пользователя (userlist)
# Патч 5    — исправление сохранения настроек значков на карточках
# Патч 6    — CSS скрытия значков + инициализация при loadProfileSettings
# Патч 7    — инициализация badge-атрибутов сразу при старте плагина
# Патч 8    — корректное отображение состояния значков в UI настроек
# Патч 9    — PAGE_SIZE 20→12 для Хочу посмотреть / Непросмотренные

import sys

SRC  = 'myshows/myshows-temp.js'
DEST = 'n-myshows.js'

with open(SRC, 'r', encoding='utf-8') as f:
    src = f.read()

errors = []

# ═══════════════════════════════════════════════════════════════════════════════
# ПАТЧ 1 — увеличиваем счётчик параллельных запросов с 4 до 5
#           (добавляем пятый запрос — userlist.Get)
# ═══════════════════════════════════════════════════════════════════════════════
P1_OLD = """                    var allData = {};
                    var loaded = 0;
                    var total = 4;"""

P1_NEW = """                    var allData = {};
                    var loaded = 0;
                    var total = 5;"""

if P1_OLD in src:
    src = src.replace(P1_OLD, P1_NEW, 1)
    print('Patch 1 OK')
else:
    errors.append('Patch 1: якорь не найден — "var total = 4"')


# ═══════════════════════════════════════════════════════════════════════════════
# ПАТЧ 2 — добавляем запрос userlist.Get после myshowsCancelled
#           результат сохраняется в allData.userlists
# ═══════════════════════════════════════════════════════════════════════════════
P2_OLD = """                    Api.myshowsCancelled({
                        page: 1
                    }, function(result) {
                        allData.cancelled = result;
                        checkComplete(\"cancelled\");
                    }, function() {
                        checkComplete(\"cancelled_err\");
                    });"""

P2_NEW = P2_OLD + """
                    makeMyShowsJSONRPCRequest('userlist.Get', {}, function(success, data) {
                        allData.userlists = (success && data && data.result) ? data.result : [];
                        checkComplete('userlists');
                    });"""

if P2_OLD in src:
    src = src.replace(P2_OLD, P2_NEW, 1)
    print('Patch 2 OK')
else:
    errors.append('Patch 2: якорь не найден — блок Api.myshowsCancelled')


# ═══════════════════════════════════════════════════════════════════════════════
# ПАТЧ 3 — переписываем блок buildLines:
#   • подборки вставляются сразу после «Непросмотренных сериалов»
#   • стандартные ряды (Хочу посмотреть) — после подборок
#   • порядок подборок задаётся массивом USERLIST_ORDER
#   • слоты lineSlots гарантируют порядок при асинхронном TMDB-обогащении
#   • кнопка «Ещё» передаёт listId в компонент myshows_userlist
# ═══════════════════════════════════════════════════════════════════════════════
P3_OLD = """                        addLine(\"Хочу посмотреть\", allData.watchlist && allData.watchlist.results, allData.watchlist && allData.watchlist.total_pages, \"myshows_watchlist\");
                        addLine(\"История\", allData.watched && allData.watched.results, allData.watched && allData.watched.total_pages, \"myshows_watched\");
                        addLine(\"Бросил смотреть\", allData.cancelled && allData.cancelled.results, allData.cancelled && allData.cancelled.total_pages, \"myshows_cancelled\");
                        if (typeof window.surs_getCustomButtonsRow === \"function\") {
                            var sursParts = [];
                            window.surs_getCustomButtonsRow(sursParts);
                            if (sursParts.length > 0) {
                                sursParts[0](function(buttonsData) {
                                    if (buttonsData && buttonsData.results && buttonsData.results.length) lines.unshift(buttonsData);
                                    finish();
                                });
                                return;
                            }
                        }
                        finish();"""

P3_NEW = """                        function finishWithSurs() {
                            // Стандартные ряды добавляются после пользовательских подборок
                            addLine(\"Хочу посмотреть\", allData.watchlist && allData.watchlist.results, allData.watchlist && allData.watchlist.total_pages, \"myshows_watchlist\");
                            if (typeof window.surs_getCustomButtonsRow === \"function\") {
                                var sursParts = [];
                                window.surs_getCustomButtonsRow(sursParts);
                                if (sursParts.length > 0) {
                                    sursParts[0](function(buttonsData) {
                                        if (buttonsData && buttonsData.results && buttonsData.results.length) lines.unshift(buttonsData);
                                        finish();
                                    });
                                    return;
                                }
                            }
                            finish();
                        }

                        // Пользовательские подборки — сразу после «Непросмотренных сериалов»
                        // Порядок отображения задаётся массивом USERLIST_ORDER.
                        // Чтобы изменить порядок или добавить подборку — отредактируй этот массив в patch.py
                        var USERLIST_ORDER = [
                            'Планы. Фильмы',
                            'Планы. Сериалы',
                            'Планы. Аниме'
                        ];
                        var USERLIST_PAGE_SIZE = 12;

                        var userlists = allData.userlists || [];
                        if (!userlists.length) {
                            finishWithSurs();
                            return;
                        }

                        // Сортируем по приоритету из USERLIST_ORDER, остальные — в конец
                        userlists.sort(function(a, b) {
                            var ai = USERLIST_ORDER.indexOf(a.title);
                            var bi = USERLIST_ORDER.indexOf(b.title);
                            if (ai === -1 && bi === -1) return 0;
                            if (ai === -1) return 1;
                            if (bi === -1) return -1;
                            return ai - bi;
                        });

                        var listsTotal = userlists.length;
                        var listsLoaded = 0;
                        var userlistResults = {};

                        userlists.forEach(function(list) {
                            makeMyShowsJSONRPCRequest('userlist.GetById', { listId: list.id }, function(success, listData) {
                                if (success && listData && listData.result) {
                                    var result = listData.result;
                                    var items = [];
                                    (result.movies || []).forEach(function(e) {
                                        var m = e.movie || e;
                                        if (m && m.id) items.push({
                                            myshowsId: m.id,
                                            title: m.title || m.titleOriginal,
                                            originalTitle: m.titleOriginal || m.title,
                                            year: m.year,
                                            type: 'movie',
                                            name: null
                                        });
                                    });
                                    (result.shows || []).forEach(function(e) {
                                        var s = e.show || e;
                                        if (s && s.id) items.push({
                                            myshowsId: s.id,
                                            title: s.title || s.titleOriginal,
                                            originalTitle: s.titleOriginal || s.title,
                                            year: s.year,
                                            type: 'show',
                                            name: s.title
                                        });
                                    });
                                    if (items.length) {
                                        userlistResults[list.id] = {
                                            items: items,
                                            totalCount: items.length
                                        };
                                    }
                                }
                                listsLoaded++;
                                if (listsLoaded === listsTotal) {
                                    var pending = 0;
                                    userlists.forEach(function(l) {
                                        if (userlistResults[l.id]) pending++;
                                    });
                                    if (!pending) { finishWithSurs(); return; }

                                    // lineSlots фиксирует порядок при асинхронном TMDB-обогащении
                                    var sortedWithData = [];
                                    userlists.forEach(function(l) {
                                        if (userlistResults[l.id]) sortedWithData.push(l);
                                    });

                                    var lineSlots = new Array(sortedWithData.length);
                                    var enriched = 0;

                                    sortedWithData.forEach(function(l, idx) {
                                        var entry = userlistResults[l.id];
                                        (function(listObj, listEntry, slotIdx) {
                                            var listTotalPages = Math.ceil(listEntry.totalCount / USERLIST_PAGE_SIZE);
                                            getTMDBDetailsSimple(listEntry.items.slice(0, USERLIST_PAGE_SIZE), function(result) {
                                                if (result && result.results && result.results.length) {
                                                    lineSlots[slotIdx] = {
                                                        title: listObj.title,
                                                        results: result.results.slice(0, USERLIST_PAGE_SIZE),
                                                        total_pages: listTotalPages,
                                                        params: {
                                                            module: Lampa.Maker.module('Line').only('Items', 'Create', 'More', 'Event'),
                                                            emit: {
                                                                onMore: function() {
                                                                    Lampa.Activity.push({
                                                                        url: '',
                                                                        title: listObj.title,
                                                                        component: 'myshows_userlist',
                                                                        listId: listObj.id,
                                                                        page: 1
                                                                    });
                                                                }
                                                            }
                                                        }
                                                    };
                                                }
                                                enriched++;
                                                if (enriched === pending) {
                                                    lineSlots.forEach(function(slot) {
                                                        if (slot) lines.push(slot);
                                                    });
                                                    finishWithSurs();
                                                }
                                            });
                                        })(l, entry, idx);
                                    });
                                }
                            });
                        });
                        return;"""

if P3_OLD in src:
    src = src.replace(P3_OLD, P3_NEW, 1)
    print('Patch 3 OK')
else:
    errors.append('Patch 3: якорь не найден — блок addLine Хочу посмотреть/История/Бросил')


# ═══════════════════════════════════════════════════════════════════════════════
# ПАТЧ 4 — добавляем компонент myshows_userlist
#           открывается кнопкой «Ещё» в ряду подборки
#           Пагинация: список грузится один раз (один API-запрос), далее
#           TMDB-обогащение и отдача по USERLIST_COMP_PAGE_SIZE элементов на страницу.
#           onNext читает уже закэшированный _allItems без повторного API-запроса.
# ═══════════════════════════════════════════════════════════════════════════════
P4_OLD = """        addCategoryComponent(\"myshows_watchlist\", Api.myshowsWatchlist, true);
        addCategoryComponent(\"myshows_watched\", Api.myshowsWatched, true);
        addCategoryComponent(\"myshows_cancelled\", Api.myshowsCancelled, true);
        addCategoryComponent(\"myshows_unwatched\", Api.myshowsUnwatched, false);
    }"""

P4_NEW = """        addCategoryComponent(\"myshows_watchlist\", Api.myshowsWatchlist, true);
        addCategoryComponent(\"myshows_watched\", Api.myshowsWatched, true);
        addCategoryComponent(\"myshows_cancelled\", Api.myshowsCancelled, true);
        addCategoryComponent(\"myshows_unwatched\", Api.myshowsUnwatched, false);

        // Компонент полного списка пользовательской подборки (открывается кнопкой «Ещё»)
        // Пагинация: список грузится один раз, страницы отдаются по USERLIST_COMP_PAGE_SIZE элементов.
        // Lampa при прокрутке вниз мутирует object.page++ и вызывает onNext.
        Lampa.Component.add('myshows_userlist', function(object) {
            var USERLIST_COMP_PAGE_SIZE = 12;
            // Кэш сырых элементов подборки — грузится один раз в onCreate
            var _allItems = null;

            var comp = Lampa.Maker.make('Category', object, function(module) {
                return module.toggle(module.MASK.base, 'Pagination');
            });

            function _parseMsItems(result) {
                var items = [];
                (result.movies || []).forEach(function(e) {
                    var m = e.movie || e;
                    if (m && m.id) items.push({
                        myshowsId: m.id,
                        title: m.title || m.titleOriginal,
                        originalTitle: m.titleOriginal || m.title,
                        year: m.year,
                        type: 'movie',
                        name: null
                    });
                });
                (result.shows || []).forEach(function(e) {
                    var s = e.show || e;
                    if (s && s.id) items.push({
                        myshowsId: s.id,
                        title: s.title || s.titleOriginal,
                        originalTitle: s.titleOriginal || s.title,
                        year: s.year,
                        type: 'show',
                        name: s.title
                    });
                });
                return items;
            }

            function _getPage(pageNum, allItems, callback) {
                var start = (pageNum - 1) * USERLIST_COMP_PAGE_SIZE;
                var pageItems = allItems.slice(start, start + USERLIST_COMP_PAGE_SIZE);
                var totalPages = Math.ceil(allItems.length / USERLIST_COMP_PAGE_SIZE) || 1;
                getTMDBDetailsSimple(pageItems, function(enriched) {
                    if (enriched && enriched.results) {
                        enriched.page = pageNum;
                        enriched.total_pages = totalPages;
                        enriched.total_results = allItems.length;
                    }
                    callback(enriched);
                });
            }

            comp.use({
                onCreate: function() {
                    this.activity.loader(true);
                    var self = this;

                    if (!getProfileSetting('myshows_token', '')) {
                        self.empty();
                        self.activity.loader(false);
                        return;
                    }

                    var listId = object.listId;
                    if (!listId) {
                        self.empty();
                        self.activity.loader(false);
                        return;
                    }

                    makeMyShowsJSONRPCRequest('userlist.GetById', { listId: listId }, function(ok, listData) {
                        if (!ok || !listData || !listData.result) {
                            self.empty();
                            self.activity.loader(false);
                            return;
                        }
                        _allItems = _parseMsItems(listData.result);
                        if (!_allItems.length) {
                            self.empty();
                            self.activity.loader(false);
                            return;
                        }
                        object.page = 1;
                        _getPage(1, _allItems, function(enriched) {
                            if (enriched && enriched.results && enriched.results.length) {
                                self.build(Lampa.Utils.addSource(enriched, 'myshows'));
                            } else {
                                self.empty();
                            }
                            self.activity.loader(false);
                        });
                    });
                },

                onNext: function(resolve, reject) {
                    if (!_allItems) { reject(); return; }
                    _getPage(object.page, _allItems, function(enriched) {
                        if (enriched && enriched.results && enriched.results.length) {
                            resolve(Lampa.Utils.addSource(enriched, 'myshows'));
                        } else {
                            reject();
                        }
                    });
                },

                onInstance: function(item, data) {
                    item.use({
                        onEnter: function() {
                            Lampa.Activity.push({
                                url: '',
                                component: 'full',
                                id: data.id,
                                method: data.name ? 'tv' : 'movie',
                                card: data
                            });
                        },
                        onFocus: function() {
                            Lampa.Background.change(Lampa.Utils.cardImgBackground(data));
                        },
                        onVisible: function() {
                            _applyProgressFromMap(data);
                            addProgressMarkerToCard(this.html, data);
                        },
                        onUpdate: function() {
                            _applyProgressFromMap(data);
                            addProgressMarkerToCard(this.html, data);
                        }
                    });
                }
            });

            return comp;
        });
    }"""

if P4_OLD in src:
    src = src.replace(P4_OLD, P4_NEW, 1)
    print('Patch 4 OK')
else:
    errors.append('Patch 4: якорь не найден — блок addCategoryComponent')


# ═══════════════════════════════════════════════════════════════════════════════
# ПАТЧ 5 — исправляем onChange для трёх badge-настроек
#   Проблема оригинала: setProfileSetting писал булево false которое
#   Lampa.Storage не умеет хранить (превращает в пустую строку).
#   Решение: пишем строку "true"/"false" напрямую через Lampa.Storage.set,
#   и сразу применяем data-атрибут скрытия на body через CSS.
# ═══════════════════════════════════════════════════════════════════════════════
P5_OLD = '''            onChange: function(value) {
                setProfileSetting("myshows_badge_progress", value === true || value === "true");
            }'''

P5_NEW = '''            onChange: function(value) {
                var boolVal = value === true || value === "true";
                Lampa.Storage.set(getProfileKey("myshows_badge_progress"), boolVal ? "true" : "false");
                Lampa.Storage.set("myshows_badge_progress", boolVal ? "true" : "false");
                if (!boolVal) document.body.setAttribute("data-hide-badge-progress", "1");
                else document.body.removeAttribute("data-hide-badge-progress");
            }'''

P5B_OLD = '''            onChange: function(value) {
                setProfileSetting("myshows_badge_remaining", value === true || value === "true");
            }'''

P5B_NEW = '''            onChange: function(value) {
                var boolVal = value === true || value === "true";
                Lampa.Storage.set(getProfileKey("myshows_badge_remaining"), boolVal ? "true" : "false");
                Lampa.Storage.set("myshows_badge_remaining", boolVal ? "true" : "false");
                if (!boolVal) document.body.setAttribute("data-hide-badge-remaining", "1");
                else document.body.removeAttribute("data-hide-badge-remaining");
            }'''

P5C_OLD = '''            onChange: function(value) {
                setProfileSetting("myshows_badge_next", value === true || value === "true");
            }'''

P5C_NEW = '''            onChange: function(value) {
                var boolVal = value === true || value === "true";
                Lampa.Storage.set(getProfileKey("myshows_badge_next"), boolVal ? "true" : "false");
                Lampa.Storage.set("myshows_badge_next", boolVal ? "true" : "false");
                if (!boolVal) document.body.setAttribute("data-hide-badge-next", "1");
                else document.body.removeAttribute("data-hide-badge-next");
            }'''

if P5_OLD in src:
    src = src.replace(P5_OLD, P5_NEW, 1)
    print('Patch 5 OK')
else:
    errors.append('Patch 5: якорь не найден — onChange badge_progress')

if P5B_OLD in src:
    src = src.replace(P5B_OLD, P5B_NEW, 1)
    print('Patch 5b OK')
else:
    errors.append('Patch 5b: якорь не найден — onChange badge_remaining')

if P5C_OLD in src:
    src = src.replace(P5C_OLD, P5C_NEW, 1)
    print('Patch 5c OK')
else:
    errors.append('Patch 5c: якорь не найден — onChange badge_next')


# ═══════════════════════════════════════════════════════════════════════════════
# ПАТЧ 6 — CSS скрытия значков + инициализация в loadProfileSettings
#   6a: добавляем CSS правила display:none для трёх классов значков
#       управляемых через data-атрибуты на body
#   6b: в loadProfileSettings читаем badge-значения из localStorage напрямую,
#       минуя Lampa.Storage (который конвертирует строку "false" в true
#       через третий аргумент), и сразу применяем data-атрибуты
# ═══════════════════════════════════════════════════════════════════════════════
P6A_OLD = (
    '        document.head.appendChild(style);\n'
    '    }\n'
    '    function addMyShowsData(data, oncomplite) {'
)

P6A_NEW = (
    '        // Патч: CSS для скрытия значков через data-атрибуты на body\n'
    '        var styleHide = document.createElement("style");\n'
    '        styleHide.textContent = [\n'
    '            "body[data-hide-badge-progress] .myshows-progress { display: none !important; }",\n'
    '            "body[data-hide-badge-remaining] .myshows-remaining { display: none !important; }",\n'
    '            "body[data-hide-badge-next] .myshows-next-episode { display: none !important; }"\n'
    '        ].join("\\n");\n'
    '        document.head.appendChild(styleHide);\n'
    '        document.head.appendChild(style);\n'
    '    }\n'
    '    function addMyShowsData(data, oncomplite) {'
)

if P6A_OLD in src:
    src = src.replace(P6A_OLD, P6A_NEW, 1)
    print('Patch 6a OK')
else:
    errors.append('Patch 6a: якорь не найден — addProgressMarkerStyles appendChild')

P6B_OLD = (
    '        Lampa.Storage.set("myshows_badge_progress", getProfileSetting("myshows_badge_progress", true), true);\n'
    '        Lampa.Storage.set("myshows_badge_remaining", getProfileSetting("myshows_badge_remaining", true), true);\n'
    '        Lampa.Storage.set("myshows_badge_next", getProfileSetting("myshows_badge_next", true), true);\n'
    '        Lampa.Storage.set("myshows_badge_style", getProfileSetting("myshows_badge_style", "1"), true);\n'
    '        applyBadgeStyleAttr();\n'
    '    }'
)

P6B_NEW = (
    # Читаем из localStorage напрямую — Lampa.Storage с third arg=true
    # конвертирует строку "false" в булево true (непустая строка = truthy)
    '        Lampa.Storage.set("myshows_badge_progress", localStorage.getItem("myshows_badge_progress") !== null ? localStorage.getItem("myshows_badge_progress") : true);\n'
    '        Lampa.Storage.set("myshows_badge_remaining", localStorage.getItem("myshows_badge_remaining") !== null ? localStorage.getItem("myshows_badge_remaining") : true);\n'
    '        Lampa.Storage.set("myshows_badge_next", localStorage.getItem("myshows_badge_next") !== null ? localStorage.getItem("myshows_badge_next") : true);\n'
    '        Lampa.Storage.set("myshows_badge_style", getProfileSetting("myshows_badge_style", "1"), true);\n'
    '        applyBadgeStyleAttr();\n'
    '        // Патч: применяем data-атрибуты скрытия значков\n'
    '        (function() {\n'
    '            var p = localStorage.getItem("myshows_badge_progress");\n'
    '            var r = localStorage.getItem("myshows_badge_remaining");\n'
    '            var n = localStorage.getItem("myshows_badge_next");\n'
    '            if (p !== null && !(p === true || p === "true")) document.body.setAttribute("data-hide-badge-progress", "1");\n'
    '            else document.body.removeAttribute("data-hide-badge-progress");\n'
    '            if (r !== null && !(r === true || r === "true")) document.body.setAttribute("data-hide-badge-remaining", "1");\n'
    '            else document.body.removeAttribute("data-hide-badge-remaining");\n'
    '            if (n !== null && !(n === true || n === "true")) document.body.setAttribute("data-hide-badge-next", "1");\n'
    '            else document.body.removeAttribute("data-hide-badge-next");\n'
    '        })();\n'
    '    }'
)

if P6B_OLD in src:
    src = src.replace(P6B_OLD, P6B_NEW, 1)
    print('Patch 6b OK')
else:
    errors.append('Patch 6b: якорь не найден — loadProfileSettings badge блок')


# ═══════════════════════════════════════════════════════════════════════════════
# ПАТЧ 7 — инициализация badge-атрибутов при старте плагина
#   Проблема: initSettings (и loadProfileSettings) вызывается через 2 секунды,
#   а карточки рисуются раньше. Lampa.Storage в момент старта ещё не содержит
#   badge-значений (инициализируется позже), поэтому читаем из localStorage
#   напрямую — он доступен синхронно всегда.
#   Также синхронизируем Lampa.Storage чтобы UI настроек показывал верные значения.
# ═══════════════════════════════════════════════════════════════════════════════
P7_OLD = (
    '            initCurrentProfile();\n'
    '            applyBadgeStyleAttr();\n'
    '            registerNMSync();'
)

P7_NEW = (
    '            initCurrentProfile();\n'
    '            applyBadgeStyleAttr();\n'
    '            // Патч: синхронизируем Lampa.Storage из localStorage и применяем\n'
    '            // data-атрибуты скрытия значков сразу при старте плагина\n'
    '            ["myshows_badge_progress", "myshows_badge_remaining", "myshows_badge_next"].forEach(function(key) {\n'
    '                var v = localStorage.getItem(key);\n'
    '                if (v !== null) Lampa.Storage.set(key, v);\n'
    '            });\n'
    '            (function() {\n'
    '                var p = (localStorage.getItem("myshows_badge_progress") !== null ? localStorage.getItem("myshows_badge_progress") : true);\n'
    '                var r = (localStorage.getItem("myshows_badge_remaining") !== null ? localStorage.getItem("myshows_badge_remaining") : true);\n'
    '                var n = (localStorage.getItem("myshows_badge_next") !== null ? localStorage.getItem("myshows_badge_next") : true);\n'
    '                if (!(p === true || p === "true")) document.body.setAttribute("data-hide-badge-progress", "1");\n'
    '                if (!(r === true || r === "true")) document.body.setAttribute("data-hide-badge-remaining", "1");\n'
    '                if (!(n === true || n === "true")) document.body.setAttribute("data-hide-badge-next", "1");\n'
    '            })();\n'
    '            registerNMSync();'
)

if P7_OLD in src:
    src = src.replace(P7_OLD, P7_NEW, 1)
    print('Patch 7 OK')
else:
    errors.append('Patch 7: якорь не найден — initCurrentProfile/applyBadgeStyleAttr/registerNMSync')


# ═══════════════════════════════════════════════════════════════════════════════
# ПАТЧ 8 — корректное отображение badge-настроек в UI
#   Проблема: initBadgesSubComponent читает значения через getProfileSetting
#   которая обращается к Lampa.Storage — но к моменту открытия настроек
#   там может быть неверное значение. Читаем из localStorage напрямую.
# ═══════════════════════════════════════════════════════════════════════════════
P8_OLD = (
    '                [ "myshows_badge_progress", "myshows_badge_remaining", "myshows_badge_next" ].forEach(function(key) {\n'
    '                    var el = badgesPanel.querySelector(\'select[data-name="\' + key + \'"]\');\n'
    '                    if (el) el.value = getProfileSetting(key, true).toString();\n'
    '                });'
)

P8_NEW = (
    '                [ "myshows_badge_progress", "myshows_badge_remaining", "myshows_badge_next" ].forEach(function(key) {\n'
    '                    var el = badgesPanel.querySelector(\'select[data-name="\' + key + \'"]\');\n'
    '                    if (el) {\n'
    '                        var v = localStorage.getItem(key);\n'
    '                        el.value = (v !== null ? v : "true");\n'
    '                    }\n'
    '                });'
)

if P8_OLD in src:
    src = src.replace(P8_OLD, P8_NEW, 1)
    print('Patch 8 OK')
else:
    errors.append('Patch 8: якорь не найден — badgesPanel forEach')


# ═══════════════════════════════════════════════════════════════════════════════
# ПАТЧ 9 — PAGE_SIZE 20→12 для Хочу посмотреть / Непросмотренные
#   myshowsWatchlist использует PAGE_SIZE_W + внутренний PAGE_SIZE.
#   myshowsUnwatched и buildLines — отдельные замены.
# ═══════════════════════════════════════════════════════════════════════════════
P9A_OLD = "        function myshowsWatchlist(object, oncomplite, onerror) {\n            var currentPage = object.page || 1;\n            var PAGE_SIZE_W = 20;"
P9A_NEW = "        function myshowsWatchlist(object, oncomplite, onerror) {\n            var currentPage = object.page || 1;\n            var PAGE_SIZE_W = 12;"

P9A2_OLD = '                        var cacheKey = "watchlist";\n                        if (!cachedShuffledItems[cacheKey]) {\n                            Lampa.Arrays.shuffle(allItems);\n                            cachedShuffledItems[cacheKey] = allItems.slice();\n                        } else allItems = cachedShuffledItems[cacheKey].slice();\n                        var PAGE_SIZE = 20;'
P9A2_NEW = '                        var cacheKey = "watchlist";\n                        if (!cachedShuffledItems[cacheKey]) {\n                            Lampa.Arrays.shuffle(allItems);\n                            cachedShuffledItems[cacheKey] = allItems.slice();\n                        } else allItems = cachedShuffledItems[cacheKey].slice();\n                        var PAGE_SIZE = 12;'

P9D_OLD = "        function myshowsUnwatched(object, oncomplite, onerror) {\n            var PAGE_SIZE = 20;"
P9D_NEW = "        function myshowsUnwatched(object, oncomplite, onerror) {\n            var PAGE_SIZE = 12;"

P9E_OLD = "                    function buildLines() {\n                        var lines = [];\n                        var PAGE_SIZE = 20;"
P9E_NEW = "                    function buildLines() {\n                        var lines = [];\n                        var PAGE_SIZE = 12;"

if P9A_OLD in src:
    src = src.replace(P9A_OLD, P9A_NEW, 1)
    print('Patch 9a OK')
else:
    errors.append('Patch 9a: якорь не найден — myshowsWatchlist PAGE_SIZE_W')

if P9A2_OLD in src:
    src = src.replace(P9A2_OLD, P9A2_NEW, 1)
    print('Patch 9a2 OK')
else:
    errors.append('Patch 9a2: якорь не найден — _doFetchWatchlist inner PAGE_SIZE')

if P9D_OLD in src:
    src = src.replace(P9D_OLD, P9D_NEW, 1)
    print('Patch 9d OK')
else:
    errors.append('Patch 9d: якорь не найден — myshowsUnwatched PAGE_SIZE')

if P9E_OLD in src:
    src = src.replace(P9E_OLD, P9E_NEW, 1)
    print('Patch 9e OK')
else:
    errors.append('Patch 9e: якорь не найден — buildLines PAGE_SIZE')


# ═══════════════════════════════════════════════════════════════════════════════
# Итог
# ═══════════════════════════════════════════════════════════════════════════════
if errors:
    print('\nОШИБКИ:')
    for e in errors:
        print(' ✗', e)
    print('\nОригинал изменился — обнови якоря в myshows-patch.py')
    sys.exit(1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(src)

print(f'\n✓ Готово: {DEST}')
