import datetime
import typing as t

import sqlalchemy as sa

from backend.webapi.models import Build, Item, db_session


def get_options() -> dict[str, t.Any]:
    res: dict[str, t.Any] = {}
    res["season"] = db_session.scalars(
        sa.select(Build.season).distinct().order_by(Build.season.asc())
    ).all()
    res["league"] = db_session.scalars(
        sa.select(Build.league).distinct().order_by(Build.league.asc())
    ).all()
    res["phase"] = db_session.scalars(
        sa.select(Build.phase).distinct().order_by(Build.phase.asc())
    ).all()
    res["date"] = [
        date.isoformat()
        if date
        else datetime.date(year=2012, month=5, day=31).isoformat()
        for date in db_session.execute(
            sa.select(sa.func.min(Build.date), sa.func.max(Build.date))
        ).one()
    ]
    res["game_i"] = db_session.scalars(
        sa.select(Build.game_i).distinct().order_by(Build.game_i.asc())
    ).all()
    res["win"] = db_session.scalars(
        sa.select(Build.win).distinct().order_by(Build.win.desc())
    ).all()
    res["game_length"] = [
        time.isoformat() if time else datetime.time().isoformat()
        for time in db_session.execute(
            sa.select(sa.func.min(Build.game_length), sa.func.max(Build.game_length))
        ).one()
    ]
    res["kda_ratio"] = [
        kda_ratio if kda_ratio else 0
        for kda_ratio in db_session.execute(
            sa.select(sa.func.min(Build.kda_ratio), sa.func.max(Build.kda_ratio))
        ).one()
    ]
    res["kills"] = [
        kills if kills else 0
        for kills in db_session.execute(
            sa.select(sa.func.min(Build.kills), sa.func.max(Build.kills))
        ).one()
    ]
    res["deaths"] = [
        deaths if deaths else 0
        for deaths in db_session.execute(
            sa.select(sa.func.min(Build.deaths), sa.func.max(Build.deaths))
        ).one()
    ]
    res["assists"] = [
        assists if assists else 0
        for assists in db_session.execute(
            sa.select(sa.func.min(Build.assists), sa.func.max(Build.assists))
        ).one()
    ]
    res["role"] = db_session.scalars(
        sa.select(Build.role).distinct().order_by(Build.role.asc())
    ).all()
    res["god_class"] = db_session.scalars(
        sa.select(Build.god_class).distinct().order_by(Build.god_class.asc())
    ).all()
    res["team1"] = db_session.scalars(
        sa.select(Build.team1).distinct().order_by(Build.team1.asc())
    ).all()
    res["player1"] = db_session.scalars(
        sa.select(Build.player1).distinct().order_by(sa.func.upper(Build.player1).asc())
    ).all()
    res["god1"] = db_session.scalars(
        sa.select(Build.god1).distinct().order_by(Build.god1.asc())
    ).all()

    res["team2"] = db_session.scalars(
        sa.select(Build.team2).distinct().order_by(Build.team2.asc())
    ).all()
    res["player2"] = db_session.scalars(
        sa.select(Build.player2).distinct().order_by(sa.func.upper(Build.player2).asc())
    ).all()
    res["god2"] = db_session.scalars(
        sa.select(Build.god2).distinct().order_by(Build.god2.asc())
    ).all()
    res["relic"] = db_session.scalars(
        sa.select(Item.name)
        .where(Item.is_relic.is_(True))
        .distinct()
        .order_by(Item.name.asc())
    ).all()
    res["item"] = db_session.scalars(
        sa.select(Item.name)
        .where(Item.is_relic.is_(False))
        .distinct()
        .order_by(Item.name.asc())
    ).all()
    return res
