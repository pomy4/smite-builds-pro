import sys

import be.backend
import be.models
from be.models import Build, Item


def images_to_base64() -> None:
    for item in Item.select():
        try:
            b64_image_data, was_compressed = be.models.compress_and_base64_image(
                item.image_data
            )
            if was_compressed:
                be.models.save_item_icon_to_archive(item, item.image_data)
            item.image_data = b64_image_data
            item.save()
        except Exception:
            print(be.models.no_img(item))
            raise


def change_few_names() -> None:
    # Remove diacritics.
    rename("Brìz", "Briz")
    rename("Dashboarřd", "Dashboarrd")
    # Fix inconsistent case.
    rename("hydrogen", "Hydrogen")
    rename("moswal", "Moswal")
    rename("trypno", "Trypno")
    rename("Ugly1", "ugly1")
    # Make more accurate (hopefully).
    rename("Elleon", "ELLEON")
    rename("EruptCrimson", "ErupTCrimson")
    rename("LeMoGow", "LeMogow")
    rename("Magicfeet", "MagicFeet")
    rename("MastkiII", "MastKiII")
    rename("Chinfu", "ChinFu")


def rename(before: str, after: str):
    player1_cnt = Build.update(player1=after).where(Build.player1 == before).execute()
    player2_cnt = Build.update(player2=after).where(Build.player2 == before).execute()
    print(f"{before} > {after} in {player1_cnt} builds.")
    print(f"{before} > {after} in {player2_cnt} builds.")
    if not player1_cnt:
        raise RuntimeError


if __name__ == "__main__":
    with be.models.db:
        with be.models.db.atomic() as txn:
            arg = sys.argv[1]
            if arg == "1":
                images_to_base64()
            elif arg == "2":
                change_few_names()
            be.models.update_last_modified(be.backend.what_time_is_it())
