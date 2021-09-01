const DateTime = luxon.DateTime;

const CATEGORIES = ['single', 'multi', 'coop', 'pvp']
CATEGORY_NAMES = {
    single: 'Single-player',
    multi: 'Multi-player',
    coop: 'Co-op',
    pvp: 'PvP',
}

class CategoryFilter {
    init(params) {
        const id = `filter_${params.colDef.field}`;
        const options = [e('option', {value: ''}), ...CATEGORIES.map(c => e('option', {value: c}, CATEGORY_NAMES[c]))];
        const select = e('select', {id}, options);
        const label = e('label', {for: id}, 'Category');
        this.gui = e('div', {class: 'catFilter'}, e('div', {style: 'display: inline-block; width: 200px'}, [label, select]));
        select.addEventListener('change', () => this.setModel(select.value));
        this.select = select;
        this.filterActive = false;
        this.filterChangedCallback = params.filterChangedCallback;
    }

    getGui() {
        return this.gui;
    }

    doesFilterPass(params) {
        return params.data.categories && params.data.categories[this.filter];
    }

    isFilterActive() {
        return this.filterActive;
    }

    getModel() {
        return this.filter;
    }

    setModel(model) {
        model = model.toString();
        if (model !== '' && !CATEGORIES.includes(model)) return;
        this.filter = model;
        this.filterActive = this.filter !== '';
        if (this.select.value !== model) this.select.value = model;
        this.filterChangedCallback();
    }
}

class CategoryFloatingFilter {
    init(params) {
        const options = [e('option', {value: ''}), ...CATEGORIES.map(c => e('option', {value: c}, CATEGORY_NAMES[c]))];
        const select = e('select', {}, options);
        this.gui = e('div', {}, select);
        this.select = select;
        select.addEventListener('change', () => params.parentFilterInstance(i => i.setModel(select.value)));
    }

    onParentModelChanged(model) {
        if (model !== '' && !CATEGORIES.includes(model)) return;
        if (this.select.value !== model) this.select.value = model;
    }

    getGui() {
        return this.gui;
    }
}

const e = (() => {
    const text = t => document.createTextNode(t);
    const attrMap = {class: 'className', for: 'htmlFor'}
    return (tag, attrs = {}, children = []) => {
        const element = document.createElement(tag);
        if (tag === 'img' && attrs['title']) attrs['alt'] = attrs['alt'] ?? attrs['title'];
        for (const [name, value] of Object.entries(attrs)) {
            element[attrMap[name] ?? name] = value;
        }
        if (children) {
            if (!Array.isArray(children)) children = [children];
            for (const c of children) element.appendChild(typeof (c) === 'string' ? text(c) : c);
        }
        return element;
    }
})();
const formatNum1 = (() => {
    const f = Intl.NumberFormat('en-US', {minimumFractionDigits: 1, maximumFractionDigits: 1});
    return value => f.format(value).replace(',', "'");
})();
const yesNo = value => value ? 'yes' : 'no';
const imageCell = params => params.value ? e('img', {src: params.value, class: 'icon', alt: ''}) : e('span');
const platformsCell = ({value: v}) => e('span', {class: 'platforms'}, v.split(',')
    .map(p => e('img', {src: `res/p-${p}.svg`, alt: p})));
const categoriesCell = params => e('span', {class: 'categories'}, params.value
    ? CATEGORIES.map(c => e('img', {
        src: `res/c-${c}.png`,
        title: `${CATEGORY_NAMES[c]}: ${yesNo(params.value[c])}`,
        class: yesNo(params.value[c])
    }))
    : []);
const playTimeCell = params => e('span', {class: 'playtime'}, params.value > 0 ? `${formatNum1(params.value / 60)}\u202Fh` : '')
const lastPlayedCell = params => {
    if (!params.value) return null;
    const d = DateTime.fromSQL(params.value);
    const diff = d.diffNow();
    return e('span', {class: 'lastPlayed', title: d.toFormat('dd.MM.yyyy HH:mm')},
        diff.toMillis() > 0 ? 'in the future' :
            diff.as('hour') > -1 ? 'minutes ago' :
                diff.as('hour') > -2 ? 'an hour ago' :
                    diff.as('day') > -1 ? `${-Math.round(diff.as('hour'))} hours ago` :
                        diff.as('day') > -2 ? 'a day ago' :
                            diff.as('month') > -1 ? `${-Math.round(diff.as('day'))} days ago` :
                                diff.as('month') > -2 ? `a month ago` :
                                    diff.as('year') > -1 ? `${-Math.round(diff.as('month'))} months ago` :
                                        diff.as('year') > -2 ? 'a year ago' :
                                            `${-Math.round(diff.as('year'))} years ago`
    )
}
const ratingCell = ({value: v}) => e('span', {class: 'rating', title: `${v} stars`}, "⭐".repeat(v))
const friendsCell = ({value: v}) => v.length ? e('span',
    {class: 'friends', title: v.map(f => friendsInfo[f].name).join('\n')},
    v.map(f => e('img', {src: friendsInfo[f].icon, alt: friendsInfo[f].name}))) : null;
const gridOptions = {
    columnDefs: [
        {
            headerName: "",
            field: "icon",
            cellRenderer: imageCell,
            width: 48,
            filter: false,
            suppressMenu: true,
            resizable: false,
            floatingFilter: false,
            sortable: false,
        },
        {field: "title", width: 300},
        {
            field: "platforms",
            cellRenderer: platformsCell,
            width: 100
        },
        {
            field: "categories",
            cellRenderer: categoriesCell,
            width: 130,
            filter: 'categoryFilter',
            floatingFilterComponent: 'categoryFloatingFilter',
        },
        {
            headerName: "Played",
            field: "gameTime",
            cellRenderer: playTimeCell,
            cellClass: "rightAligned",
            width: 80
        },
        {
            field: "lastPlayed",
            cellRenderer: lastPlayedCell,
            width: 110
        },
        {
            field: "rating",
            cellRenderer: ratingCell,
            width: 110
        },
        {
            field: "friends",
            hide: !showFriends,
            cellRenderer: friendsCell,
            width: 170,
            filterParams: {
                textFormatter: t => t.map ? t.map(f => friendsInfo[f].name).join(',').toLowerCase() : t.toLowerCase()
            }
        }
    ],
    components: {
        categoryFilter: CategoryFilter,
        categoryFloatingFilter: CategoryFloatingFilter,
    },
    defaultColDef: {
        filter: 'agTextColumnFilter',
        floatingFilter: true,
        resizable: true,
        sortable: true,
        lockVisible: true,
    },
    onCellMouseOver(evt) {
        showDetails(evt.node.data);
    },
    rowData: data,
    enableCellTextSelection: true,
};
let showDetails;
document.addEventListener('DOMContentLoaded', () => {
    const gridDiv = document.querySelector('#myGrid');
    new agGrid.Grid(gridDiv, gridOptions);

    const details = document.querySelector('#details');
    const title = details.querySelector('h1');
    const cover = details.querySelector('#cover');
    const background = details.querySelector('#background');
    const backgroundImg = background.querySelector('img');
    const summary = details.querySelector('#summary');
    let detailRow = {};

    showDetails = (() => {
        return (node) => {
            if (detailRow == node) return;
            detailRow = node;
            title.innerText = node.title;
            cover.src = node.cover;
            backgroundImg.src = node.icon;
            summary.innerText = node.summary;
        }
    })();

    document.querySelector('#exportInfo').addEventListener('mouseover', () => {
        detailRow = {};
        title.innerText = "g-export";
        cover.src = 'res/logo-cover.svg';
        backgroundImg.src = 'res/logo-cover.svg';
        summary.innerText = "© Gilles Waeber 2021\n\n" +
            "Powered by: Ag-Grid Community (MIT), Luxon (MIT)\n" +
            "Game covers, icons, and summaries from GOG, game categories from Steam\n" +
            "Platform icon sources:" +
            "Ionicons (https://ionic.io/ionicons): xbox, " +
            "SVGRepo (https://www.svgrepo.com): epic, generic, " +
            "Icon8 (https://icons8.com) steam, gog, uplay, origin, rockstar, battlenet\n" +
            "Logos/covers/icons copyrighted by respective owners";
    })
});