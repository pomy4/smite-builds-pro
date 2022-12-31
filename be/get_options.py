import datetime

import peewee as pw

from be.models import Build, Item


def get_options() -> dict:
    res = {}
    res["season"] = [
        b.season
        for b in Build.select(Build.season).distinct().order_by(Build.season.asc())
    ]
    res["league"] = [
        b.league
        for b in Build.select(Build.league).distinct().order_by(Build.league.asc())
    ]
    res["phase"] = [
        b.phase
        for b in Build.select(Build.phase).distinct().order_by(Build.phase.asc())
    ]
    res["date"] = [
        date.isoformat()
        if date
        else datetime.date(year=2012, month=5, day=31).isoformat()
        for date in Build.select(pw.fn.MIN(Build.date), pw.fn.MAX(Build.date)).scalar(
            as_tuple=True
        )
    ]
    res["game_i"] = [
        b.game_i
        for b in Build.select(Build.game_i).distinct().order_by(Build.game_i.asc())
    ]
    res["win"] = [
        b.win for b in Build.select(Build.win).distinct().order_by(Build.win.desc())
    ]
    res["game_length"] = [
        time.isoformat() if time else datetime.time().isoformat()
        for time in Build.select(
            pw.fn.MIN(Build.game_length), pw.fn.MAX(Build.game_length)
        ).scalar(as_tuple=True)
    ]
    res["kda_ratio"] = [
        kda_ratio if kda_ratio else 0
        for kda_ratio in Build.select(
            pw.fn.MIN(Build.kda_ratio), pw.fn.MAX(Build.kda_ratio)
        ).scalar(as_tuple=True)
    ]
    res["kills"] = [
        kills if kills else 0
        for kills in Build.select(
            pw.fn.MIN(Build.kills), pw.fn.MAX(Build.kills)
        ).scalar(as_tuple=True)
    ]
    res["deaths"] = [
        deaths if deaths else 0
        for deaths in Build.select(
            pw.fn.MIN(Build.deaths), pw.fn.MAX(Build.deaths)
        ).scalar(as_tuple=True)
    ]
    res["assists"] = [
        assists if assists else 0
        for assists in Build.select(
            pw.fn.MIN(Build.assists), pw.fn.MAX(Build.assists)
        ).scalar(as_tuple=True)
    ]
    res["role"] = [
        b.role for b in Build.select(Build.role).distinct().order_by(Build.role.asc())
    ]
    res["team1"] = [
        b.team1
        for b in Build.select(Build.team1).distinct().order_by(Build.team1.asc())
    ]
    res["player1"] = [
        b.player1
        for b in Build.select(Build.player1)
        .distinct()
        .order_by(pw.fn.Upper(Build.player1).asc())
    ]
    res["god1"] = [
        b.god1 for b in Build.select(Build.god1).distinct().order_by(Build.god1.asc())
    ]
    res["team2"] = [
        b.team2
        for b in Build.select(Build.team2).distinct().order_by(Build.team2.asc())
    ]
    res["player2"] = [
        b.player2
        for b in Build.select(Build.player2)
        .distinct()
        .order_by(pw.fn.Upper(Build.player2).asc())
    ]
    res["god2"] = [
        b.god2 for b in Build.select(Build.god2).distinct().order_by(Build.god2.asc())
    ]
    res["relic"] = [
        b.relic1.name
        for b in (
            Build.select(Item.name).join(Item, on=Build.relic1)
            | Build.select(Item.name).join(Item, on=Build.relic2)
        ).order_by(Item.name.asc())
    ]
    res["item"] = [
        b.item1.name
        for b in (
            Build.select(Item.name).join(Item, on=Build.item1)
            | Build.select(Item.name).join(Item, on=Build.item2)
            | Build.select(Item.name).join(Item, on=Build.item3)
            | Build.select(Item.name).join(Item, on=Build.item4)
            | Build.select(Item.name).join(Item, on=Build.item5)
            | Build.select(Item.name).join(Item, on=Build.item6)
        ).order_by(Item.name.asc())
    ]
    return res
