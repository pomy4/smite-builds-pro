import time
import urllib.error
import urllib.request

from models import Build, Item, db

cdn_images_url = "https://webcdn.hirezstudios.com/smite/item-icons"


def rename(table, where, new_column, new_value):
    query = table.select().where(where)
    for row in query:
        setattr(row, new_column, new_value)
        row.save()


def rename_v2(table, where, **renames):
    query = table.select().where(where)
    for row in query:
        for new_column, new_value in renames.items():
            setattr(row, new_column, new_value)
        row.save()


def get_image(image_name):
    request = urllib.request.Request(
        f"{cdn_images_url}/{image_name}", headers={"User-Agent": "Mozilla"}
    )
    with urllib.request.urlopen(request) as f:
        image_data = f.read()
        time.sleep(0.25)
        return image_data
    # except urllib.error.URLError as e:


def get_item(image_name, index):
    items = list(Item.select().where(Item.image_name == image_name))
    return items[index]


def fix_role(match_id, game_i, player1, wrong_role, correct_role):
    build = (
        Build.select()
        .where(
            (Build.match_id == match_id)
            & (Build.game_i == game_i)
            & (Build.player1 == player1)
            & (Build.role == wrong_role)
        )
        .first()
    )
    if build is None:
        return
    build.role = correct_role
    build.save()
    fix_player2_and_god2(match_id, game_i, player1, build.player2)


def fix_player2_and_god2(match_id, game_i, player1, wrong_player2):
    build = (
        Build.select()
        .where(
            (Build.match_id == match_id)
            & (Build.game_i == game_i)
            & (Build.player1 == player1)
            & (Build.player2 == wrong_player2)
        )
        .first()
    )
    if build is None:
        return
    role = build.role
    opp_team = build.team2
    opp_build = (
        Build.select()
        .where(
            (Build.match_id == match_id)
            & (Build.game_i == game_i)
            & (Build.role == role)
            & (Build.team1 == opp_team)
        )
        .first()
    )
    build.player2 = opp_build.player1
    build.god2 = opp_build.god1
    build.save()


def fix_name(old_name, new_name):
    for build in Build.select().where(Build.player1 == old_name):
        build.player1 = new_name
        build.save()
    for build in Build.select().where(Build.player2 == old_name):
        build.player2 = new_name
        build.save()


db.connect()

# SEASON 8

sunder = get_item("sundering-spear.jpg", 0)
sunder_upgrade = get_item("sundering-spear-upgrade.jpg", 0)
beads = get_item("purification-beads.jpg", 0)
beads_upgrade = get_item("purification-beads-upgrade.jpg", 0)
aegis = get_item("aegis-amulet.jpg", 0)
blink = get_item("blink-rune.jpg", 0)
frenzy = get_item("belt-of-frenzy.jpg", 0)
ankh_upgrade = get_item("cursed-ankh-upgrade.jpg", 0)
horrific_upgrade = get_item("horrific-emblem-upgrade.jpg", 0)
vamp_shroud = get_item("vampiric-shroud.jpg", 0)
charon = get_item("charons-coin.jpg", 0)
spear_of_deso = get_item("spear-of-desolation.jpg", 0)
divine_ruin = get_item("divine-ruin.jpg", 0)
soul_reaver = get_item("soul-reaver.jpg", 0)
spellbook = get_item("spellbook.jpg", 0)
manikin = get_item("manikin-scepter.jpg", 0)
pythags = get_item("pythagorems-piece.jpg", 0)
magus = get_item("spear-of-the-magus.jpg", 0)
bancroft_t2 = get_item("talon-trinket.jpg", 0)
conduit = get_item("conduit-gem.jpg", 0)
chronos = get_item("chronos-pendant.jpg", 0)
soul_gem = get_item("soul-gem.jpg", 0)
obs_shard = get_item("obsidian-shard.jpg", 0)

rename(
    Item,
    Item.image_name == "bloodsoaked-shroud.jpg",
    "image_name",
    "blood-soaked-shroud.jpg",
)
rename(
    Item,
    Item.image_name == "pointed-shuriken.jpg",
    "image_name",
    "8-pointed-shuriken.jpg",
)
rename(
    Item,
    (Item.image_name == "blood-soaked-shroud.jpg") & (Item.image_data == None),
    "image_data",
    get_image("blood-soaked-shroud.jpg"),
)
rename(
    Item,
    (Item.image_name == "8-pointed-shuriken.jpg") & (Item.image_data == None),
    "image_data",
    get_image("8-pointed-shuriken.jpg"),
)
rename(Build, Build.player1 == "AwesomeJake408", "player1", "Awesomejake408")
rename(Build, Build.player2 == "AwesomeJake408", "player2", "Awesomejake408")
rename(
    Build,
    (Build.match_id == 2736)
    & (Build.game_i == 1)
    & (Build.player1 == "sLainy")
    & (Build.role == "Coach"),
    "role",
    "Solo",
)
rename(
    Build,
    (Build.match_id == 2736)
    & (Build.game_i == 2)
    & (Build.player1 == "sLainy")
    & (Build.role == "Coach"),
    "role",
    "Solo",
)
rename_v2(
    Build,
    (Build.match_id == 2736)
    & (Build.game_i == 1)
    & (Build.player1 == "sLainy")
    & (Build.player2 == "Missing data"),
    player2="Haddix",
    god2="King Arthur",
)
rename_v2(
    Build,
    (Build.match_id == 2736)
    & (Build.game_i == 2)
    & (Build.player1 == "sLainy")
    & (Build.player2 == "Missing data"),
    player2="Haddix",
    god2="Gilgamesh",
)
rename_v2(
    Build,
    (Build.match_id == 2736)
    & (Build.game_i == 1)
    & (Build.player1 == "Haddix")
    & (Build.player2 == "Missing data"),
    player2="sLainy",
    god2="Xing Tian",
)
rename_v2(
    Build,
    (Build.match_id == 2736)
    & (Build.game_i == 2)
    & (Build.player1 == "Haddix")
    & (Build.player2 == "Missing data"),
    player2="sLainy",
    god2="Xing Tian",
)
rename_v2(
    Build,
    (Build.match_id == 2736)
    & (Build.game_i == 1)
    & (Build.player1 == "Awesomejake408")
    & (Build.relic2 == None),
    relic1=sunder,
    relic2=frenzy,
)
rename_v2(
    Build,
    (Build.match_id == 2736)
    & (Build.game_i == 2)
    & (Build.player1 == "Awesomejake408")
    & (Build.relic2 == None),
    relic1=beads,
    relic2=sunder_upgrade,
)
rename_v2(
    Build,
    (Build.match_id == 2736)
    & (Build.game_i == 1)
    & (Build.player1 == "Inbowned")
    & (Build.relic2 == None),
    relic1=beads,
    relic2=sunder_upgrade,
)
rename_v2(
    Build,
    (Build.match_id == 2736)
    & (Build.game_i == 2)
    & (Build.player1 == "Inbowned")
    & (Build.relic2 == None),
    relic1=blink,
    relic2=sunder,
)
rename_v2(
    Build,
    (Build.match_id == 2743)
    & (Build.game_i == 1)
    & (Build.player1 == "Awesomejake408")
    & (Build.relic2 == None),
    relic1=beads,
    relic2=sunder_upgrade,
)
rename_v2(
    Build,
    (Build.match_id == 2743)
    & (Build.game_i == 2)
    & (Build.player1 == "Awesomejake408")
    & (Build.relic2 == None),
    relic1=horrific_upgrade,
    relic2=sunder_upgrade,
)
rename_v2(
    Build,
    (Build.match_id == 2743)
    & (Build.game_i == 1)
    & (Build.player1 == "Ronngyu")
    & (Build.relic2 == None),
    relic1=sunder_upgrade,
    relic2=ankh_upgrade,
)
rename_v2(
    Build,
    (Build.match_id == 2743)
    & (Build.game_i == 2)
    & (Build.player1 == "Ronngyu")
    & (Build.relic2 == None),
    relic1=sunder_upgrade,
    relic2=beads_upgrade,
)
rename_v2(
    Build,
    (Build.match_id == 2743)
    & (Build.game_i == 1)
    & (Build.player1 == "Panitom")
    & (Build.relic2 == None),
    relic1=beads,
    relic2=sunder_upgrade,
)
if (
    not Build.select()
    .where(
        (Build.match_id == 2736) & (Build.game_i == 1) & (Build.player1 == "oBoronic")
    )
    .exists()
):
    default = (
        Build.select()
        .where(
            (Build.match_id == 2736) & (Build.game_i == 1) & (Build.player1 == "sLainy")
        )
        .get()
    )
    new = Build(
        season=default.season,
        league=default.league,
        phase=default.phase,
        date=default.date,
        match_id=default.match_id,
        game_i=default.game_i,
        win=default.win,
        game_length=default.game_length,
        kda_ratio=1.5,
        kills=0,
        deaths=2,
        assists=3,
        role="Mid",
        god1="Merlin",
        player1="oBoronic",
        team1=default.team1,
        god2="Tiamat",
        player2="Venenu",
        team2=default.team2,
        relic1=beads,
        relic2=aegis,
        item1=vamp_shroud,
        item2=charon,
        item3=spear_of_deso,
        item4=divine_ruin,
        item5=soul_reaver,
        item6=None,
    )
    new.save()
if (
    not Build.select()
    .where(
        (Build.match_id == 2736) & (Build.game_i == 2) & (Build.player1 == "oBoronic")
    )
    .exists()
):
    default = (
        Build.select()
        .where(
            (Build.match_id == 2736) & (Build.game_i == 2) & (Build.player1 == "sLainy")
        )
        .get()
    )
    new = Build(
        season=default.season,
        league=default.league,
        phase=default.phase,
        date=default.date,
        match_id=default.match_id,
        game_i=default.game_i,
        win=default.win,
        game_length=default.game_length,
        kda_ratio=1 / 3,
        kills=0,
        deaths=3,
        assists=1,
        role="Mid",
        god1="Raijin",
        player1="oBoronic",
        team1=default.team1,
        god2="Vulcan",
        player2="Venenu",
        team2=default.team2,
        relic1=beads,
        relic2=aegis,
        item1=vamp_shroud,
        item2=charon,
        item3=divine_ruin,
        item4=spear_of_deso,
        item5=spellbook,
        item6=None,
    )
    new.save()

if (
    not Build.select()
    .where(
        (Build.match_id == 2981) & (Build.game_i == 1) & (Build.player1 == "oBoronic")
    )
    .exists()
):
    default = (
        Build.select()
        .where(
            (Build.match_id == 2981) & (Build.game_i == 1) & (Build.player1 == "Stuart")
        )
        .get()
    )
    new = Build(
        season=default.season,
        league=default.league,
        phase=default.phase,
        date=default.date,
        match_id=default.match_id,
        game_i=default.game_i,
        win=default.win,
        game_length=default.game_length,
        kda_ratio=1,
        kills=1,
        deaths=4,
        assists=3,
        role="Mid",
        god1="Sol",
        player1="oBoronic",
        team1=default.team1,
        god2="Raijin",
        player2="Hurriwind",
        team2=default.team2,
        relic1=beads,
        relic2=aegis,
        item1=manikin,
        item2=pythags,
        item3=magus,
        item4=divine_ruin,
        item5=bancroft_t2,
        item6=None,
    )
    new.save()

if (
    not Build.select()
    .where(
        (Build.match_id == 2981) & (Build.game_i == 2) & (Build.player1 == "oBoronic")
    )
    .exists()
):
    default = (
        Build.select()
        .where(
            (Build.match_id == 2981) & (Build.game_i == 2) & (Build.player1 == "Stuart")
        )
        .get()
    )
    new = Build(
        season=default.season,
        league=default.league,
        phase=default.phase,
        date=default.date,
        match_id=default.match_id,
        game_i=default.game_i,
        win=default.win,
        game_length=default.game_length,
        kda_ratio=10,
        kills=3,
        deaths=1,
        assists=7,
        role="Mid",
        god1="Raijin",
        player1="oBoronic",
        team1=default.team1,
        god2="Tiamat",
        player2="Hurriwind",
        team2=default.team2,
        relic1=beads,
        relic2=aegis,
        item1=conduit,
        item2=chronos,
        item3=soul_gem,
        item4=soul_reaver,
        item5=obs_shard,
        item6=None,
    )
    new.save()

if (
    not Build.select()
    .where(
        (Build.match_id == 2981) & (Build.game_i == 3) & (Build.player1 == "oBoronic")
    )
    .exists()
):
    default = (
        Build.select()
        .where(
            (Build.match_id == 2981) & (Build.game_i == 3) & (Build.player1 == "Stuart")
        )
        .get()
    )
    new = Build(
        season=default.season,
        league=default.league,
        phase=default.phase,
        date=default.date,
        match_id=default.match_id,
        game_i=default.game_i,
        win=default.win,
        game_length=default.game_length,
        kda_ratio=5 / 3,
        kills=2,
        deaths=3,
        assists=3,
        role="Mid",
        god1="Tiamat",
        player1="oBoronic",
        team1=default.team1,
        god2="Sol",
        player2="Hurriwind",
        team2=default.team2,
        relic1=beads,
        relic2=aegis,
        item1=conduit,
        item2=chronos,
        item3=divine_ruin,
        item4=soul_reaver,
        item5=obs_shard,
        item6=None,
    )
    new.save()

fix_player2_and_god2(2736, 1, "Venenu", "Missing data")
fix_player2_and_god2(2736, 2, "Venenu", "Missing data")
fix_player2_and_god2(2981, 1, "Hurriwind", "Missing data")
fix_player2_and_god2(2981, 2, "Hurriwind", "Missing data")
fix_player2_and_god2(2981, 3, "Hurriwind", "Missing data")

# Too lazy to fix
# duck3y missing
# 4188|8|SPL|SWC Placements - Group B|2021-12-16|3376|1|1|00:21:06|14.0|7|1|7|Jungle|Gilgamesh|LASBRA|BOLTS|Missing data|Missing data|VALKS|1|9|60|229|105|51|15|180
# 4197|8|SPL|SWC Placements - Group B|2021-12-16|3376|2|1|00:23:10|6.0|3|0|3|Jungle|Cliodhna|LASBRA|BOLTS|Missing data|Missing data|VALKS|1|2|93|105|122|77|108|78
# 4202|8|SPL|SWC Placements - Group B|2021-12-16|3376|3|1|00:27:35|10.0|3|0|7|Jungle|Loki|LASBRA|BOLTS|Missing data|Missing data|VALKS|1|9|15|132|77|54|106|

# SEASON 9

rename_v2(
    Build,
    (Build.match_id == 3528)
    & (Build.game_i == 1)
    & (Build.player1 == "Benji")
    & (Build.role == "Coach"),
    role="Solo",
    player2="Jarcorrr",
    god2="Bellona",
)
rename_v2(
    Build,
    (Build.match_id == 3528)
    & (Build.game_i == 1)
    & (Build.player1 == "Jarcorrr")
    & (Build.player2 == "Missing data"),
    player2="Benji",
    god2="Cthulhu",
)
rename_v2(
    Build,
    (Build.match_id == 3559)
    & (Build.game_i == 1)
    & (Build.player1 == "JinguBang")
    & (Build.role == "Sub"),
    role="Jungle",
    player2="Oathhh",
    god2="Susano",
)
rename_v2(
    Build,
    (Build.match_id == 3559)
    & (Build.game_i == 1)
    & (Build.player1 == "ChinFu")
    & (Build.role == "Jungle"),
    role="ADC",
    player2="dudemanbro429",
    god2="Medusa",
)
rename_v2(
    Build,
    (Build.match_id == 3559)
    & (Build.game_i == 1)
    & (Build.player1 == "dudemanbro429")
    & (Build.player2 == "Missing data"),
    player2="ChinFu",
    god2="Jing Wei",
)
rename_v2(
    Build,
    (Build.match_id == 3567)
    & (Build.game_i == 1)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="oGryph",
    god2="Heimdallr",
)
rename_v2(
    Build,
    (Build.match_id == 3567)
    & (Build.game_i == 1)
    & (Build.player1 == "oGryph")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Medusa",
)
rename_v2(
    Build,
    (Build.match_id == 3567)
    & (Build.game_i == 2)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="oGryph",
    god2="Heimdallr",
)
rename_v2(
    Build,
    (Build.match_id == 3567)
    & (Build.game_i == 2)
    & (Build.player1 == "oGryph")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Medusa",
)
rename_v2(
    Build,
    (Build.match_id == 3567)
    & (Build.game_i == 3)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="oGryph",
    god2="Chiron",
)
rename_v2(
    Build,
    (Build.match_id == 3567)
    & (Build.game_i == 3)
    & (Build.player1 == "oGryph")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Medusa",
)
rename_v2(
    Build,
    (Build.match_id == 3569)
    & (Build.game_i == 1)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="Hydrogen",
    god2="Charybdis",
)
rename_v2(
    Build,
    (Build.match_id == 3569)
    & (Build.game_i == 1)
    & (Build.player1 == "Hydrogen")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Medusa",
)
rename_v2(
    Build,
    (Build.match_id == 3569)
    & (Build.game_i == 2)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="Hydrogen",
    god2="Jing Wei",
)
rename_v2(
    Build,
    (Build.match_id == 3569)
    & (Build.game_i == 2)
    & (Build.player1 == "Hydrogen")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Medusa",
)

rename(
    Item,
    Item.image_name == "faeblessed-hoops.jpg",
    "image_name",
    "fae-blessed-hoops.jpg",
)
rename(
    Item,
    (Item.image_name == "fae-blessed-hoops.jpg") & (Item.image_data == None),
    "image_data",
    get_image("fae-blessed-hoops.jpg"),
)

rename_v2(
    Build,
    (Build.match_id == 3599)
    & (Build.game_i == 1)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="TottiGR",
    god2="Rama",
)
rename_v2(
    Build,
    (Build.match_id == 3599)
    & (Build.game_i == 1)
    & (Build.player1 == "TottiGR")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Artemis",
)
rename_v2(
    Build,
    (Build.match_id == 3599)
    & (Build.game_i == 2)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="TottiGR",
    god2="Rama",
)
rename_v2(
    Build,
    (Build.match_id == 3599)
    & (Build.game_i == 2)
    & (Build.player1 == "TottiGR")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Artemis",
)
rename_v2(
    Build,
    (Build.match_id == 3602)
    & (Build.game_i == 1)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="VaporishCoast",
    god2="Heimdallr",
)
rename_v2(
    Build,
    (Build.match_id == 3602)
    & (Build.game_i == 1)
    & (Build.player1 == "VaporishCoast")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Artemis",
)
rename_v2(
    Build,
    (Build.match_id == 3602)
    & (Build.game_i == 2)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="VaporishCoast",
    god2="Rama",
)
rename_v2(
    Build,
    (Build.match_id == 3602)
    & (Build.game_i == 2)
    & (Build.player1 == "VaporishCoast")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Izanami",
)
rename_v2(
    Build,
    (Build.match_id == 3603)
    & (Build.game_i == 1)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="TottiGR",
    god2="Rama",
)
rename_v2(
    Build,
    (Build.match_id == 3603)
    & (Build.game_i == 1)
    & (Build.player1 == "TottiGR")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Jing Wei",
)
rename_v2(
    Build,
    (Build.match_id == 3603)
    & (Build.game_i == 2)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="TottiGR",
    god2="Chernobog",
)
rename_v2(
    Build,
    (Build.match_id == 3603)
    & (Build.game_i == 2)
    & (Build.player1 == "TottiGR")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Rama",
)
rename_v2(
    Build,
    (Build.match_id == 3610)
    & (Build.game_i == 1)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="Echrome",
    god2="Hachiman",
)
rename_v2(
    Build,
    (Build.match_id == 3610)
    & (Build.game_i == 1)
    & (Build.player1 == "Echrome")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Rama",
)
rename_v2(
    Build,
    (Build.match_id == 3610)
    & (Build.game_i == 2)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="Echrome",
    god2="Hachiman",
)
rename_v2(
    Build,
    (Build.match_id == 3610)
    & (Build.game_i == 2)
    & (Build.player1 == "Echrome")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Rama",
)
rename_v2(
    Build,
    (Build.match_id == 3611)
    & (Build.game_i == 1)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="oGryph",
    god2="Rama",
)
rename_v2(
    Build,
    (Build.match_id == 3611)
    & (Build.game_i == 1)
    & (Build.player1 == "oGryph")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Chernobog",
)
rename_v2(
    Build,
    (Build.match_id == 3611)
    & (Build.game_i == 2)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="oGryph",
    god2="Heimdallr",
)
rename_v2(
    Build,
    (Build.match_id == 3611)
    & (Build.game_i == 2)
    & (Build.player1 == "oGryph")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Rama",
)
rename_v2(
    Build,
    (Build.match_id == 3611)
    & (Build.game_i == 3)
    & (Build.player1 == "dudemanbro429")
    & (Build.role == "Sub"),
    role="ADC",
    player2="oGryph",
    god2="Heimdallr",
)
rename_v2(
    Build,
    (Build.match_id == 3611)
    & (Build.game_i == 3)
    & (Build.player1 == "oGryph")
    & (Build.player2 == "Missing data"),
    player2="dudemanbro429",
    god2="Jing Wei",
)

fix_role(3795, 2, "thebestotter", "Coach", "Support")
fix_role(3795, 2, "Privative", "Support", "Solo")
fix_player2_and_god2(3795, 2, "NotGeno", "Privative")
fix_player2_and_god2(3795, 2, "RelentlessOne", "Missing data")

fix_role(3792, 1, "Biteyyy", "Sub", "ADC")
fix_role(3792, 2, "Biteyyy", "Sub", "ADC")
fix_role(3792, 3, "Biteyyy", "Sub", "ADC")
fix_player2_and_god2(3792, 1, "Diesel", "Missing data")
fix_player2_and_god2(3792, 2, "Diesel", "Missing data")
fix_player2_and_god2(3792, 3, "Diesel", "Missing data")

fix_role(3794, 1, "MagicFeet", "Sub", "Jungle")
fix_role(3794, 2, "MagicFeet", "Sub", "Jungle")
fix_player2_and_god2(3794, 1, "Oathhh", "Missing data")
fix_player2_and_god2(3794, 2, "Oathhh", "Missing data")

fix_role(3804, 1, "Baskin", "Sub", "Support")
fix_role(3804, 2, "Baskin", "Sub", "Support")
fix_player2_and_god2(3804, 1, "Hurriwind", "Missing data")
fix_player2_and_god2(3804, 2, "Hurriwind", "Missing data")

fix_name("LeMoGoW", "LeMoGow")
fix_name("ErupTCrimson", "EruptCrimson")
fix_name("ELLEON", "Elleon")
fix_name("MastKiII", "MastkiII")
fix_name("MagicFeet", "Magicfeet")
fix_name("ChinFu", "Chinfu")
fix_name("Calvìn", "Calvin")
fix_name("Briz", "Brìz")


# Too lazy to fix
# Set missing
# Pre-Season Friday, 2022 March 25 Atlantis Leviathans VS Valhalla Valkyries LVTHN 2 - 0 VALKS (match_id 3472)
# slaaaaaaasH missing
# 5702|9|SCC|NA Phase 1|2022-03-31|3550|1|0|00:34:55|0.0|0|5|0|Solo|Cliodhna|Remakami|HOUND|Missing data|Missing data|SAGES|258|256|29|70|257|31|51|15
# 5715|9|SCC|NA Phase 1|2022-03-31|3550|2|1|00:28:26|5.0|1|0|4|Solo|Odin|Remakami|HOUND|Missing data|Missing data|SAGES|258|260|202|229|257|31|124|155
# 5724|9|SCC|NA Phase 1|2022-03-31|3550|3|1|00:24:09|5.0|1|0|4|Solo|Osiris|Remakami|HOUND|Missing data|Missing data|SAGES|258|260|171|229|30|47|115|124
# 5837|9|SCC|NA Phase 1|2022-04-09|3561|1|1|00:39:04|2.25|2|4|7|Solo|Jormungandr|Uzzy|STORM|Missing data|Missing data|SAGES|278|285|139|257|219|176|87|124
# 5850|9|SCC|NA Phase 1|2022-04-09|3561|2|1|00:31:25|7.0|1|1|6|Solo|Camazotz|Uzzy|STORM|Missing data|Missing data|SAGES|273|275|202|47|229|51|70|32
# 5885|9|SCC|NA Phase 1|2022-04-14|3562|1|1|00:22:33|8.0|2|1|6|Solo|Sun Wukong|RelentlessOne|WRDNS|Missing data|Missing data|SAGES|273|269|29|70|229|32|214|
# 5898|9|SCC|NA Phase 1|2022-04-14|3562|2|1|00:23:51|6.5|4|2|9|Solo|Amaterasu|RelentlessOne|WRDNS|Missing data|Missing data|SAGES|282|275|190|47|128|140|51|
# CaptainQuig missing
# 5786|9|SCC|NA Phase 1|2022-04-07|3559|1|0|00:31:59|1.75|2|4|5|Support|Atlas|Dashboarřd|WEAVE|Missing data|Missing data|HOUND|264|258|17|19|87|128|20|
# 5795|9|SCC|NA Phase 1|2022-04-07|3559|2|0|00:31:20|0.625|0|8|5|Support|Khepri|Dashboarřd|WEAVE|Missing data|Missing data|HOUND|268|264|34|19|20|128||
# Rapio missing
# 9334|9|SCC|EU Phase 2|2022-06-16|3803|2|1|00:34:25|21.0|10|1|11|Jungle|Awilix|Dzoni|MAMBO|Missing data|Missing data|RAVEN|276|270|10|78|46|106|77|107
# BIGSLIMTIMMYJIM missing
# 9649|9|SCC|NA Phase 2|2022-06-16|3792|1|0|00:35:05|1.0|1|4|3|Support|Khepri|Hurriwind|YOMI|Missing data|Missing data|WEAVE|282|262|17|21|87|128|35|
# delnyy missing
# 9685|9|SCC|NA Phase 2|2022-06-16|3795|1|1|00:26:42|12.0|6|1|6|Solo|Bastet|RelentlessOne|WRDNS|Missing data|Missing data|SAGES|276|258|227|70|30|87|15|

import update_last_modified

db.close()