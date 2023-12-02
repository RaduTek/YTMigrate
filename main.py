import functools
import os
import json
from typing import Tuple
from datetime import datetime

import ytmusicapi
from ytmusicapi import YTMusic, setup_oauth

version = "1.0"
config_filename = "config.json"


def prompt_yes_no(message: str, default_yes: bool = True) -> bool:
    while True:
        sel = input(message + (" [Y/n] " if default_yes else " [y/N] "))
        if not sel:
            return default_yes
        elif sel in "yY":
            return True
        elif sel in "nN":
            return False


def write_backup(data: list | dict, type: str) -> bool:
    try:
        backup_date = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        with open(f"{type}_backup_{backup_date}.json", "w") as backup_file:
            json.dump(data, backup_file)
    except Exception as e:
        print(f"Failed to save backup, {str(e)}!")
        return False
    else:
        print("Backup saved succesfully!")
        return True


def copy_likes(ytm: Tuple[YTMusic, YTMusic]):
    print("Loading liked songs from source account...", end="", flush=True)
    liked_source = ytm[0].get_playlist("LM", limit=5000)
    liked_source_ids = functools.reduce(
        lambda l, i: l + [i["videoId"]], liked_source["tracks"], []
    )

    print("\rLoading liked songs from destination account...", end="", flush=True)
    liked_dest = ytm[1].get_playlist("LM", limit=5000)
    liked_dest_ids = functools.reduce(
        lambda l, i: l + [i["videoId"]], liked_dest["tracks"], []
    )

    print("\r" + " " * 50 + "\r", end="", flush=True)

    songs_to_like = list(set(liked_source_ids) - set(liked_dest_ids))

    if len(songs_to_like) < len(liked_source_ids):
        print(
            f"Skipping {len(liked_source_ids) - len(songs_to_like)} out of "
            f"{len(liked_source_ids)} songs liked!"
        )

    if len(songs_to_like) == 0:
        print("No songs left to like!")
        return

    if not prompt_yes_no(f"Add {len(songs_to_like)} songs to likes?"):
        print("Operation cancelled!")
        return

    try:
        for index, song in enumerate(songs_to_like):
            print(
                f"\rAdding songs to likes... {index + 1}/{len(songs_to_like)}",
                end="",
                flush=True,
            )
            ytm[1].rate_song(song, "LIKE")
    except Exception as e:
        print("\nFailed to like songs,", e)
    else:
        print("\nTransferred all liked songs successfully!")


def copy_playlist(
    ytm: Tuple[YTMusic, YTMusic], playlist_id: str, playlist_name: str = ""
):
    print(f"Loading playlist: {playlist_name} - [{playlist_id}]...")
    playlist_data = ytm[0].get_playlist(playlist_id, limit=5000)
    if not playlist_data:
        print("Failed to load playlist!")
        return

    song_ids = functools.reduce(
        lambda l, i: l + [i["videoId"]], playlist_data["tracks"], []
    )

    print("Creating playlist... ", end="", flush=True)
    try:
        dest_playlist_id = ytm[1].create_playlist(
            playlist_data["title"],
            playlist_data["description"] if playlist_data["description"] else "",
            playlist_data["privacy"],
            song_ids,
        )
        # dest_playlist_id = "TEST_IS_WORKING"
        if type(dest_playlist_id) == str:
            print(
                f"\rPlaylist created successfully! URL: https://music.youtube.com/playlist?list={dest_playlist_id}"
            )
        else:
            print("\nFailed to create new playlist!")
    except Exception as e:
        print("\nFailed to create new playlist,", e)


def parse_number_ids(selection: str):
    result = []
    id_tokens = selection.split()

    for token in id_tokens:
        try:
            if "-" in token:
                start, end = map(int, token.split("-"))
                result.extend(range(start, end + 1))
            else:
                result.append(int(token))
        except ValueError:
            print(
                f"Error: Invalid format for token '{token}'. Please use a valid format."
            )
            return None
    return result


def menu_copy_playlists(ytm: Tuple[YTMusic, YTMusic]):
    print("Loading playlists from source account...", end="", flush=True)
    source_playlists = ytm[0].get_library_playlists(100)
    print("\rSelect playlists:" + " " * 30)

    all_playlists = []
    count = 0

    for playlist in source_playlists:
        # Exclude "Episodes for later" and "Liked songs" playlists
        if playlist["playlistId"] not in ("LM", "SE"):
            all_playlists += [playlist]
            count += 1
            print(
                f"{count}: {playlist['title']}"
                + (f" - {playlist['count']} songs" if "count" in playlist else "")
                + f" - [{playlist['playlistId']}]"
            )

    print("A: All playlists")
    print("C: Cancel")

    while True:
        sel = input(
            "Selection (enter playlist numbers, 'A' for all, or 'C' to cancel): "
        )
        sel_playlists = []

        if sel.lower() == "c":
            print("Operation cancelled!")
            return
        elif sel.lower() == "a":
            sel_playlists = all_playlists
        else:
            sel_ids = parse_number_ids(sel)
            if not sel_ids or not all(1 <= i <= count for i in sel_ids):
                print("Invalid selection. Please enter valid playlist numbers.")
                continue
            for i in sel_ids:
                sel_playlists += [all_playlists[i - 1]]

        for p in sel_playlists:
            try:
                copy_playlist(ytm, p["playlistId"], p["title"])
            except Exception as e:
                print(f"Error copying playlist '{p['title']}': {e}")
                # Handle the error appropriately, e.g., log it or prompt the user
        return


def copy_albums(ytm: Tuple[YTMusic, YTMusic]):
    print("Loading saved albums from source account...", end="", flush=True)
    albums_source = ytm[0].get_library_albums(limit=5000)
    # List of playlistId of all albums from library
    albums_source_ids = functools.reduce(
        lambda l, i: l + [i["playlistId"]], albums_source, []
    )

    print("\rLoading saved albums from destination account...", end="", flush=True)
    albums_dest = ytm[1].get_library_albums(limit=5000)
    # List of playlistId of all albums from library
    albums_dest_ids = functools.reduce(
        lambda l, i: l + [i["playlistId"]], albums_dest, []
    )

    print("\r" + " " * 50 + "\r", end="", flush=True)

    albums_to_save = list(set(albums_source_ids) - set(albums_dest_ids))

    if len(albums_to_save) < len(albums_source_ids):
        print(
            f"Skipping {len(albums_source_ids) - len(albums_to_save)} out of "
            f"{len(albums_source_ids)} albums saved!"
        )

    if len(albums_to_save) == 0:
        print("No albums left to transfer over!")
        return

    if not prompt_yes_no(
        f"Add {len(albums_to_save)} albums to destination account's library?"
    ):
        print("Operation cancelled!")
        return

    try:
        for index, album_playlist_id in enumerate(albums_to_save):
            print(
                f"\rAdding albums to likes... {index + 1}/{len(albums_to_save)}",
                end="",
                flush=True,
            )
            ytm[1].rate_playlist(album_playlist_id, "LIKE")
    except Exception as e:
        print("\nFailed to add albums,", e)
    else:
        print("\nTransferred all saved albums successfully!")


def remove_albums(ytm: YTMusic):
    print("\rLoading saved albums from selected account...", end="", flush=True)
    albums_data = ytm.get_library_albums(limit=5000)
    # List of playlistId and browseId of all albums from library
    albums_ids = functools.reduce(
        lambda l, i: l + [{"playlistId": i["playlistId"], "browseId": i["browseId"]}],
        albums_data,
        [],
    )

    print("\r" + " " * 50 + "\r", end="", flush=True)

    if len(albums_ids) == 0:
        print("No albums left to remove!")
        return

    print("Removed album IDs will be saved to a JSON file for safety.")
    if not prompt_yes_no(
        f"Remove {len(albums_ids)} albums from the selected account's library?"
    ):
        print("Operation cancelled!")
        return

    try:
        backup_date = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        with open(f"albums_backup_{backup_date}.json", "w") as backup_file:
            json.dump(albums_ids, backup_file)
    except Exception as e:
        print(f"Failed to save backup, {str(e)}, aborting!")
        return
    else:
        print("Backup saved succesfully!")

    try:
        for index, album in enumerate(albums_ids):
            print(
                f"\rRemoving albums from library... {index + 1}/{len(albums_ids)}",
                end="",
                flush=True,
            )
            ytm.rate_playlist(album["playlistId"], "INDIFFERENT")
    except Exception as e:
        print("\nFailed to remove albums,", e)
    else:
        print("\nRemoved all saved albums successfully!")


def removal_tools(ytm: Tuple[YTMusic, YTMusic]):
    selected_ytm = ytm[0]
    while True:
        sel = input("Select an account [0=source / 1=destination]: ")
        if sel == "0" or sel == "1":
            selected_ytm = ytm[int(sel)]
            break
        else:
            print("Invalid input!")

    while True:
        print("\nWARNING: These operation are permanent and cannot be undone.")
        print("Removal tools:")
        print("  1. Remove saved albums")
        print("  0. Back")
        sel = input("Your selection: ")
        match sel:
            case "0":
                return
            case "1":
                remove_albums(selected_ytm)
            case _:
                print("Invalid selection:", sel)


def menu_main(ytm: Tuple[YTMusic, YTMusic]):
    while True:
        print("\nMain menu:")
        print("Copy tools:")
        print("  1. Copy playlists")
        print("  2. Copy likes")
        print("  3. Copy albums")
        print("Other tools:")
        print("  4. Removal tools")
        print("  0. Exit")
        sel = input("Your selection: ")
        match sel:
            case "0":
                return
            case "1":
                menu_copy_playlists(ytm)
            case "2":
                copy_likes(ytm)
            case "3":
                copy_albums(ytm)
            case "4":
                removal_tools(ytm)
            case _:
                print("Invalid option:", sel)


def check_config() -> bool:
    if not os.path.isfile(config_filename):
        print("Configuration file not found!")
        return False
    return True


def do_auth() -> Tuple[YTMusic, YTMusic] | None:
    with open(config_filename, "r") as config_file:
        try:
            config = json.load(config_file)
            ytm = None
            try:
                ytm = (
                    YTMusic(json.dumps(config["source_account"]["oauth_headers"])),
                    YTMusic(json.dumps(config["dest_account"]["oauth_headers"])),
                )
            except Exception as e:
                print("Authentication failed:", e)
            else:
                print("Authentication successful!")
            return ytm
        except Exception as e:
            print("Failed to load configuration:", str(e))
            return None


def setup_auth() -> bool:
    print("Set up accounts:")
    config = {
        "source_account": {"oauth_headers": {}},
        "dest_account": {"oauth_headers": {}},
    }

    print("Log in with Oauth for source account:")
    config["source_account"]["oauth_headers"] = ytmusicapi.setup_oauth()

    print("Log in with Oauth for destination account:")
    config["dest_account"]["oauth_headers"] = ytmusicapi.setup_oauth()

    print("Writing configuration file...")
    try:
        with open(config_filename, "w") as json_file:
            json.dump(config, json_file, indent=2)
    except Exception as e:
        print("Failed to create config:", str(e))
        return False
    else:
        print("Configuration created!")
    return True


def main():
    print(f"YTMigrate, version {version}\n")
    if check_config() or setup_auth():
        ytm = do_auth()
        if ytm:
            menu_main(ytm)


if __name__ == "__main__":
    main()
