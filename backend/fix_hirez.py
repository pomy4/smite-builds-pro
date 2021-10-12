from models import Build, Item, db
import urllib.request
import urllib.error
import time

cdn_images_url = 'https://webcdn.hirezstudios.com/smite/item-icons'

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
    request = urllib.request.Request(f'{cdn_images_url}/{image_name}', headers={'User-Agent': 'Mozilla'})
    with urllib.request.urlopen(request) as f:
        image_data = f.read()
        time.sleep(0.25)
        return image_data
    # except urllib.error.URLError as e:

def get_item(image_name):
    items = list(Item.select().where(Item.image_name==image_name))
    assert len(items) == 1
    return items[0]

db.connect()

sunder = get_item('sundering-spear.jpg')
sunder_upgrade = get_item('sundering-spear-upgrade.jpg')
beads = get_item('purification-beads.jpg')
beads_upgrade = get_item('purification-beads-upgrade.jpg')
aegis = get_item('aegis-amulet.jpg')
blink = get_item('blink-rune.jpg')
frenzy = get_item('belt-of-frenzy.jpg')
ankh_upgrade = get_item('cursed-ankh-upgrade.jpg')
horrific_upgrade = get_item('horrific-emblem-upgrade.jpg')
vamp_shroud = get_item('vampiric-shroud.jpg')
charon = get_item('charons-coin.jpg')
spear_of_deso = get_item('spear-of-desolation.jpg')
divine_ruin = get_item('divine-ruin.jpg')
soul_reaver = get_item('soul-reaver.jpg')
spellbook = get_item('spellbook.jpg')
manikin = get_item('manikin-scepter.jpg')
pythags = get_item('pythagorems-piece.jpg')
magus = get_item('spear-of-the-magus.jpg')
bancroft_t2 = get_item('talon-trinket.jpg')
conduit = get_item('conduit-gem.jpg')
chronos = get_item('chronos-pendant.jpg')
soul_gem = get_item('soul-gem.jpg')
obs_shard = get_item('obsidian-shard.jpg')

bss = get_image('blood-soaked-shroud.jpg')
eps = get_image('8-pointed-shuriken.jpg')

rename(Item,
    Item.image_name == 'bloodsoaked-shroud.jpg',
    'image_name', 'blood-soaked-shroud.jpg')
rename(Item,
    Item.image_name == 'pointed-shuriken.jpg',
    'image_name', '8-pointed-shuriken.jpg')
rename(Item,
    (Item.image_name == 'blood-soaked-shroud.jpg') & (Item.image_data == None),
    'image_data', bss)
rename(Item,
    (Item.image_name == '8-pointed-shuriken.jpg') & (Item.image_data == None),
    'image_data', eps)
rename(Build,
    Build.player1 == 'AwesomeJake408',
    'player1', 'Awesomejake408')
rename(Build,
    Build.player2 == 'AwesomeJake408',
    'player2', 'Awesomejake408')
rename(Build,
    (Build.match_id == 2736) & (Build.game_i == 1) & (Build.player1 == 'sLainy') & (Build.role == 'Coach'),
    'role', 'Solo')
rename(Build,
    (Build.match_id == 2736) & (Build.game_i == 2) & (Build.player1 == 'sLainy') & (Build.role == 'Coach'),
    'role', 'Solo')
rename_v2(Build,
    (Build.match_id == 2736) & (Build.game_i == 1) & (Build.player1 == 'Awesomejake408') & (Build.relic2 == None),
    relic1=frenzy, relic2=sunder)
rename_v2(Build,
    (Build.match_id == 2736) & (Build.game_i == 2) & (Build.player1 == 'Awesomejake408') & (Build.relic2 == None),
    relic1=sunder_upgrade, relic2=beads)
rename_v2(Build,
    (Build.match_id == 2736) & (Build.game_i == 1) & (Build.player1 == 'Inbowned') & (Build.relic2 == None),
    relic1=sunder_upgrade, relic2=beads)
rename_v2(Build,
    (Build.match_id == 2736) & (Build.game_i == 2) & (Build.player1 == 'Inbowned') & (Build.relic2 == None),
    relic1=sunder, relic2=blink)
rename_v2(Build,
    (Build.match_id == 2743) & (Build.game_i == 1) & (Build.player1 == 'Awesomejake408') & (Build.relic2 == None),
    relic1=sunder_upgrade, relic2=beads)
rename_v2(Build,
    (Build.match_id == 2743) & (Build.game_i == 2) & (Build.player1 == 'Awesomejake408') & (Build.relic2 == None),
    relic1=sunder_upgrade, relic2=horrific_upgrade)
rename_v2(Build,
    (Build.match_id == 2743) & (Build.game_i == 1) & (Build.player1 == 'Ronngyu') & (Build.relic2 == None),
    relic1=ankh_upgrade, relic2=sunder_upgrade)
rename_v2(Build,
    (Build.match_id == 2743) & (Build.game_i == 2) & (Build.player1 == 'Ronngyu') & (Build.relic2 == None),
    relic1=beads_upgrade, relic2=sunder_upgrade)
rename_v2(Build,
    (Build.match_id == 2743) & (Build.game_i == 1) & (Build.player1 == 'Panitom') & (Build.relic2 == None),
    relic1=sunder_upgrade, relic2=beads)
if not Build.select().where((Build.match_id == 2736) & (Build.game_i == 1) & (Build.player1 == 'oBoronic')).exists():
    default = Build.select().where((Build.match_id == 2736) & (Build.game_i == 1) & (Build.player1 == 'sLainy')).get()
    new = Build(season=default.season, league=default.league, phase=default.phase,
        date=default.date, match_id=default.match_id, game_i=default.game_i,
        win=default.win, game_length=default.game_length, kda_ratio=1.5,
        kills=0, deaths=2, assists=3, role='Mid', god1='Merlin', player1='oBoronic',
        team1=default.team1, god2='Tiamat', player2='Venenu', team2=default.team2,
        relic1=aegis, relic2=beads, item1=vamp_shroud, item2=charon,
        item3=spear_of_deso, item4=divine_ruin, item5=soul_reaver, item6=None)
    new.save()
if not Build.select().where((Build.match_id == 2736) & (Build.game_i == 2) & (Build.player1 == 'oBoronic')).exists():
    default = Build.select().where((Build.match_id == 2736) & (Build.game_i == 2) & (Build.player1 == 'sLainy')).get()
    new = Build(season=default.season, league=default.league, phase=default.phase,
        date=default.date, match_id=default.match_id, game_i=default.game_i,
        win=default.win, game_length=default.game_length, kda_ratio=1/3,
        kills=0, deaths=3, assists=1, role='Mid', god1='Raijin', player1='oBoronic',
        team1=default.team1, god2='Vulcan', player2='Venenu', team2=default.team2,
        relic1=aegis, relic2=beads, item1=vamp_shroud, item2=charon,
        item3=divine_ruin, item4=spear_of_deso, item5=spellbook, item6=None)
    new.save()
db.close()

if not Build.select().where((Build.match_id == 2981) & (Build.game_i == 1) & (Build.player1 == 'oBoronic')).exists():
    default = Build.select().where((Build.match_id == 2981) & (Build.game_i == 1) & (Build.player1 == 'Stuart')).get()
    new = Build(season=default.season, league=default.league, phase=default.phase,
        date=default.date, match_id=default.match_id, game_i=default.game_i,
        win=default.win, game_length=default.game_length, kda_ratio=1,
        kills=1, deaths=4, assists=3, role='Mid', god1='Sol', player1='oBoronic',
        team1=default.team1, god2='Raijin', player2='Hurriwind', team2=default.team2,
        relic1=beads, relic2=aegis, item1=manikin, item2=pythags,
        item3=magus, item4=divine_ruin, item5=bancroft_t2, item6=None)
    new.save()

if not Build.select().where((Build.match_id == 2981) & (Build.game_i == 2) & (Build.player1 == 'oBoronic')).exists():
    default = Build.select().where((Build.match_id == 2981) & (Build.game_i == 2) & (Build.player1 == 'Stuart')).get()
    new = Build(season=default.season, league=default.league, phase=default.phase,
        date=default.date, match_id=default.match_id, game_i=default.game_i,
        win=default.win, game_length=default.game_length, kda_ratio=10,
        kills=3, deaths=1, assists=7, role='Mid', god1='Raijin', player1='oBoronic',
        team1=default.team1, god2='Tiamat', player2='Hurriwind', team2=default.team2,
        relic1=beads, relic2=aegis, item1=conduit, item2=chronos,
        item3=soul_gem, item4=soul_reaver, item5=obs_shard, item6=None)
    new.save()

if not Build.select().where((Build.match_id == 2981) & (Build.game_i == 3) & (Build.player1 == 'oBoronic')).exists():
    default = Build.select().where((Build.match_id == 2981) & (Build.game_i == 3) & (Build.player1 == 'Stuart')).get()
    new = Build(season=default.season, league=default.league, phase=default.phase,
        date=default.date, match_id=default.match_id, game_i=default.game_i,
        win=default.win, game_length=default.game_length, kda_ratio=5/3,
        kills=2, deaths=3, assists=3, role='Mid', god1='Tiamat', player1='oBoronic',
        team1=default.team1, god2='Sol', player2='Hurriwind', team2=default.team2,
        relic1=beads, relic2=aegis, item1=conduit, item2=chronos,
        item3=divine_ruin, item4=soul_reaver, item5=obs_shard, item6=None)
    new.save()
