#!/usr/bin/env python3
# myshows-patch.py — applies our changes to the original myshows.js
# Output is written to n-myshows.js

import sys

SRC  = 'myshows/myshows-temp.js'
DEST = 'n-myshows.js'

with open(SRC, 'r', encoding='utf-8') as f:
    src = f.read()

errors = []

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 1 — total: 4 → 5 (add fifth parallel request — userlist.Get)
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
    errors.append('Patch 1: anchor not found — "var total = 4"')


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 2 — add userlist.Get request after myshowsCancelled
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
    errors.append('Patch 2: anchor not found — Api.myshowsCancelled block')


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 3 — replace buildLines block
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
                            // Standard rows — after custom lists
                            addLine(\"Хочу посмотреть\", allData.watchlist && allData.watchlist.results, allData.watchlist && allData.watchlist.total_pages, \"myshows_watchlist\");
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
                            finish();
                        }

                        // Custom user lists — displayed right after Unwatched
                        // ── List display order ────────────────────────────────
                        // To change the order or add a new list —
                        // edit this array in myshows-patch.py
                        var USERLIST_ORDER = [
                            'Планы. Фильмы',
                            'Планы. Сериалы',
                            'Планы. Аниме'
                        ];

                        var userlists = allData.userlists || [];
                        if (!userlists.length) {
                            finishWithSurs();
                            return;
                        }

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
                                    if (!pending) {
                                        finishWithSurs();
                                        return;
                                    }
                                    var lineSlots = new Array(userlists.length).fill(null);
                                    var enriched = 0;
                                    userlists.forEach(function(l, idx) {
                                        if (!userlistResults[l.id]) {
                                            enriched++;
                                            if (enriched === pending) {
                                                lineSlots.forEach(function(slot) {
                                                    if (slot) lines.push(slot);
                                                });
                                                finishWithSurs();
                                            }
                                            return;
                                        }
                                        (function(listObj, entry, slotIdx) {
                                            getTMDBDetailsSimple(entry.items, function(tmdbData) {
                                                if (tmdbData && tmdbData.results && tmdbData.results.length) {
                                                    var lineData = Lampa.Utils.addSource(tmdbData, 'myshows');
                                                    lineData.title = listObj.title;
                                                    lineData.onMore = function() {
                                                        if (listObj && listObj.id) {
                                                            Lampa.Activity.push({
                                                                url: '',
                                                                title: listObj.title,
                                                                component: 'myshows_userlist',
                                                                listId: listObj.id,
                                                                page: 1
                                                            });
                                                        }
                                                    };
                                                    lineSlots[slotIdx] = lineData;
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
    errors.append('Patch 3: anchor not found — addLine block')


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 4 — add myshows_userlist component
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

        Lampa.Component.add('myshows_userlist', function(object) {
            var comp = Lampa.Maker.make('Category', object, function(module) {
                return module.toggle(module.MASK.base, 'Pagination');
            });

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

                        getTMDBDetailsSimple(items, function(enriched) {
                            if (enriched && enriched.results && enriched.results.length) {
                                self.build(Lampa.Utils.addSource(enriched, 'myshows'));
                            } else {
                                self.empty();
                            }
                            self.activity.loader(false);
                        });
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
    errors.append('Patch 4: anchor not found — addCategoryComponent block')


# ═══════════════════════════════════════════════════════════════════════════════
# Result
# ═══════════════════════════════════════════════════════════════════════════════
if errors:
    print('\nERRORS:')
    for e in errors:
        print(' ✗', e)
    print('\nUpstream has changed — update anchors in myshows-patch.py')
    sys.exit(1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(src)

print(f'\n✓ Done: {DEST}')
