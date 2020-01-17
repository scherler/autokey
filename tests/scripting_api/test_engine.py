# Copyright (C) 2019 Thomas Hess <thomas.hess@udo.edu>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import typing
import pathlib

from unittest.mock import MagicMock, patch

import pytest
from hamcrest import *

from autokey.configmanager.configmanager import ConfigManager
from autokey.service import PhraseRunner
import autokey.model
import autokey.service
from autokey.scripting import Engine

@pytest.fixture
def create_engine() -> typing.Tuple[Engine, autokey.model.Folder]:
    # Make sure to not write to the hard disk
    test_folder = autokey.model.Folder("Test folder")
    test_folder.persist = MagicMock()

    # Mock load_global_config to add the test folder to the known folders. This causes the ConfigManager to skip it’s
    # first-run logic.
    with patch("autokey.model.Phrase.persist"), patch("autokey.model.Folder.persist"),\
         patch("autokey.configmanager.configmanager.ConfigManager.load_global_config",
               new=(lambda self: self.folders.append(test_folder))):
        engine = Engine(ConfigManager(MagicMock()), MagicMock(spec=PhraseRunner))
        engine.configManager.config_altered(False)

    return engine, test_folder

folder="create_new_folder"
@pytest.mark.parametrize("args, kwargs, error_msg", [
    [("Not a folder", "name", "contents",),
     {},
     "Folder is not checked for type=model.Folder"],
    [(folder, folder, "contents",),
     {},
     "name is not checked for type=str",],
    [(folder, "name", folder),
     {},
     "contents is not checked for type=str"],
    [(folder, "name", "contents",),
     {"abbreviations": folder},
     "abbreviations is not checked for type=str"],
    [(folder, "name", "contents",),
     {"abbreviations": ["t1", folder]},
     "abbreviations is not checked for type=list[str]"],
    [(folder, "name", "contents",),
     {"hotkey": folder},
     "hotkey is not checked for type=tuple"],
    [(folder, "name", "contents",),
     {"hotkey": (["<ctrl>"], "t", "t")},
     "hotkey is not checked for tuple len 2"],
    [(folder, "name", "contents",),
     {"hotkey": (["<ctrl>"], folder)},
     "hotkey is not checked for type=tuple(str,str)"],
    [(folder, "name", "contents",),
     {"hotkey": (["<ctrl>", folder], "a")},
     "hotkey[0] is not checked for type=list[str]"],
    [(folder, "name", "contents",),
     {"hotkey": (["Not a valid modifier"], "w")},
     "hotkey is not checked as valid Key (invalid modifier)"],
    [(folder, "name", "contents",),
     {"hotkey": ([], "train")},
     "hotkey is not checked as valid Key (invalid key)"],
    [(folder, "name", "contents",),
     {"hotkey": ("<ctrl>", "t")},
     "hotkey modifiers not checked as list."],
    # (folder, "name",
    # "contents", {"hotkey": (["<alt>"], "6")}),
    # "hotkey modifiers fails single valid str"
    # (folder, "name",
    # "contents", {"hotkey": (["<ctrl>", "<shift>"], "<alt>")}),
    # "hotkey key is allowed to be a modifier"
])
def test_engine_create_phrase_invalid_input_types_raises_value_error(create_engine, args, kwargs, error_msg):
    engine, folder = create_engine
    for arg in args:
        if arg=="create new folder":
            arg=folder
    with patch("autokey.model.Phrase.persist"):
        #     error_check = engine.create_phrase(folder, "test phrase",
    # "contents", hotkey=(["<ctrl>"], "a"))
        assert_that(
            calling(engine.create_phrase).with_args(*args, **kwargs),
            raises(ValueError), error_msg)

def test_engine_create_phrase_valid_input_types_not_raises_value_error(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Phrase.persist"):
        assert_that(
            calling(engine.create_phrase).with_args(folder, "name",
                "contents", abbreviations=["t1", "t2"]),
            not_(raises(ValueError)), "abbreviations is not checked for type=list")

def test_engine_create_phrase_adds_phrase_to_parent(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Phrase.persist"):
        phrase = engine.create_phrase(folder, "Phrase", "ABC")
        assert_that(folder.items, has_item(phrase))
        hotkey = engine.create_phrase(folder, "Phrase", "ABC", hotkey=(["<ctrl>"], "a"))
        assert_that(folder.items, has_item(hotkey))


def test_engine_create_phrase_duplicate_hotkey_raises_value_error(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Phrase.persist"):
        phrase = engine.create_phrase(folder, "Phrase", "ABC", hotkey=(["<ctrl>"], "a"))
        assert_that(folder.items, has_item(phrase))
        assert_that(
            calling(engine.create_phrase).with_args(folder, "Phrase2", "ABC", hotkey=(["<ctrl>"], "a")),
            raises(ValueError)
        )


def test_engine_create_phrase_duplicate_abbreviation_raises_value_error(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Phrase.persist"):
        phrase = engine.create_phrase(folder, "Phrase", "ABC", abbreviations="abbr")
        assert_that(folder.items, has_item(phrase))
        assert_that(
            calling(engine.create_phrase).with_args(folder, "Phrase", "ABC", abbreviations=["abbrev", "abbr"]),
            raises(ValueError)
        )


@pytest.mark.parametrize("invalid_abbreviations", [
    1337,
    ["abbr", 1337],
    b'bytes_are_invalid',
    [b'a', "ab"]
])
def test_engine_create_phrase_invalid_abbreviation_type(invalid_abbreviations, create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Phrase.persist"):
        assert_that(
            calling(engine.create_phrase).with_args(folder, "Phrase", "ABC", abbreviations=invalid_abbreviations),
            raises(ValueError)
        )


def test_engine_create_phrase_set_single_abbreviation(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Phrase.persist"):
        phrase = engine.create_phrase(folder, "Phrase", "ABC", abbreviations="abbr")
    assert_that(phrase.abbreviations, contains("abbr"))


def test_engine_create_phrase_set_list_of_abbreviations(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Phrase.persist"):
        phrase = engine.create_phrase(folder, "Phrase", "ABC", abbreviations=["abbr", "Short"])
    assert_that(phrase.abbreviations, contains_inanyorder("abbr", "Short"))


def test_engine_create_phrase_set_always_prompt(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Phrase.persist"):
        phrase_without_prompt = engine.create_phrase(folder, "Phrase", "ABC", always_prompt=False)
        phrase_with_prompt = engine.create_phrase(folder, "Phrase2", "ABC", always_prompt=True)
    assert_that(phrase_with_prompt.prompt, is_(equal_to(True)))
    assert_that(phrase_without_prompt.prompt, is_(equal_to(False)))


def test_engine_create_phrase_set_show_in_tray(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Phrase.persist"):
        phrase_not_in_tray = engine.create_phrase(folder, "Phrase", "ABC", show_in_system_tray=False)
        phrase_in_tray = engine.create_phrase(folder, "Phrase2", "ABC", show_in_system_tray=True)
    assert_that(phrase_in_tray.show_in_tray_menu, is_(equal_to(True)))
    assert_that(phrase_not_in_tray.show_in_tray_menu, is_(equal_to(False)))


@pytest.mark.parametrize("send_mode", Engine.SendMode)
def test_engine_create_phrase_set_send_mode(send_mode: Engine.SendMode, create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Phrase.persist"):
        phrase = engine.create_phrase(folder, "Phrase", "ABC", send_mode=send_mode)
    assert_that(phrase.sendMode, is_(equal_to(send_mode)))


def test_engine_create_nontemp_phrase_with_temp_parent_raises_value_error(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Folder.persist"):
        parent = engine.create_folder("parent",
            parent_folder=folder, temporary=True)
        assert_that(
            calling(engine.create_phrase).with_args(parent, "phrase", "ABC", temporary=False),
            raises(ValueError)
        )


def test_engine_create_folder_invalid_types_raises_value_error(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Folder.persist"):
        assert_that(
            calling(engine.create_folder).with_args(folder),
            raises(ValueError), "title is not checked for type=str")
        assert_that(
            calling(engine.create_folder).with_args("title", "not a folder"),
            raises(ValueError), "parent_folder is not checked for type=model.Folder")
        assert_that(
            calling(engine.create_folder).with_args("title", folder),
            not_(raises(ValueError)), "parent_folder erroneously fails check for type=model.Folder")
        assert_that(
            calling(engine.create_folder).with_args("title", pathlib.Path(".")),
            not_(raises(ValueError)), "parent_folder erroneously fails check for type=pathlib.Path")
        assert_that(
            calling(engine.create_folder).with_args("title", temporary="not a bool"),
            raises(ValueError), "temporary is not checked for type=bool")


def test_engine_create_folder(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Folder.persist"):
        test_folder = engine.create_folder("New folder")
        assert_that(engine.configManager.allFolders, has_item(test_folder), "doesn't create new top-level folder")


def test_engine_create_folder_subfolder(create_engine):
    engine, folder = create_engine
    # Temporary: prevent persisting (which fails b/c folder doesn't exist).
    test_folder = engine.create_folder("New folder",
            parent_folder=folder, temporary=True)
    assert_that(engine.configManager.allFolders, not_(has_item(test_folder)), "creates top-level folder instead of subfolder")
    assert_that(folder, is_(equal_to(test_folder.parent)),
        "Doesn't add parent folder as parent of subfolder")
    assert_that(folder.folders,
        has_item(test_folder),
            "Doesn't create subfolder in correct folder")
    test_folder = engine.create_folder("New folder",
            parent_folder=folder, temporary=True)
    assert_that(engine.configManager.allFolders, not_(has_item(test_folder)), "creates top-level folder instead of subfolder")

def test_engine_create_nontemp_subfolder_with_temp_parent_raises_value_error(create_engine):
    engine, folder = create_engine
    with patch("autokey.model.Folder.persist"):
        parent = engine.create_folder("parent",
            parent_folder=folder, temporary=True)
        assert_that(
            calling(engine.create_folder).with_args("child", parent_folder=parent, temporary=False),
            raises(ValueError)
        )


def test_engine_create_folder_from_path(create_engine):
    engine, folder = create_engine
    path = pathlib.Path("/tmp/autokey")
    title = "path folder"
    fullpath=path / title
    fullpathStr="/tmp/autokey/path folder"
    # fullpathStr=str(fullpath)
    with patch("autokey.model.Folder.persist"):
        with patch("pathlib.Path.mkdir"):
            test_folder = engine.create_folder(title, parent_folder=path)
            # XXX This is probably an erroneous assertion.
            assert_that(engine.configManager.allFolders, has_item(test_folder), "Doesn't create folder from path")
            assert_that(test_folder.path, is_(equal_to(fullpathStr)), "Doesn't create folder from path")
        assert_that(
            calling(engine.create_folder).with_args(title, parent_folder=path),
            not_(raises(Exception)), "Adding a duplicate folder from path raises error")
            # assert_that(path.exists())
            # path.rmdir()


def test_engine_remove_temporary_toplevel(create_engine):
    engine, folder = create_engine
    # Folder acts as a non-temp top-level folder.
    test_phrase = engine.create_phrase(folder, "test phrase",
        "contents", temporary=True)
    with patch("autokey.model.Phrase.persist"):
        test_phrase_nontemp = engine.create_phrase(folder,
                "test phrase nontemp", "contents")
    test_folder = engine.create_folder("New folder",
            temporary=True)

    engine.remove_all_temporary()

    assert_that(engine.configManager.allFolders,
            has_item(folder),
                "Removes non-temp top-level folders")
    assert_that(engine.configManager.allFolders,
            not_(has_item(test_folder)),
                "doesn't remove temp top-level folders")
    assert_that(folder.items,
            not_(has_item(test_phrase)),
                "doesn't remove temp phrases")

def test_engine_remove_temporary(create_engine):
    engine, folder = create_engine

    test_subfolder = engine.create_folder("New folder",
            parent_folder=folder, temporary=True)
    test_phrase = engine.create_phrase(test_subfolder, "test phrase",
    "contents", temporary=True)
    # No longer permitted behavior
    # with patch("autokey.model.Folder.persist"):
    #     test_subfolder_nontemp = engine.create_folder("New subfolder",
    #             parent_folder = folder)
    #     test_subsubfolder_nontemp = engine.create_folder(
    #             "New subfolder nontemp",
    #             parent_folder = test_subfolder)
    # with patch("autokey.model.Phrase.persist"):
    #     test_phrase_nontemp = engine.create_phrase(test_subfolder,
    #             "test phrase nontemp", "contents")

    engine.remove_all_temporary()

    assert_that(folder.folders,
            not_(has_item(test_subfolder)),
                "doesn't remove temp subfolders")
    assert_that(test_subfolder.items,
            not_(is_(equal_to(test_phrase))),
                "doesn't remove temp phrases from temp subfolders")
    # assert_that(folder.folders,
    #         has_item(test_subfolder_nontemp),
    #             "Removes non-temp subfolders")
    # Non-temp children are no longer permitted.
    # Removes non-temp from temp parents.
    # assert_that(test_subfolder.items,
    #         not_(has_item(test_phrase_nontemp)),
    #             "doesn't remove nontemp phrases from temp subfolders")
    # assert_that(test_subfolder.folders,
    #         not_(has_item(test_subsubfolder_nontemp)),
    #             "doesn't remove nontemp subfolders from temp parent folders")
    test_hotkey = engine.create_phrase(folder, "test hotkey",
    "contents", hotkey=(["<ctrl>"], "a"), temporary=True)
    assert_that(
        calling(engine.create_phrase).with_args(folder, "test hotkey2",
                                                "contents", hotkey=(["<ctrl>"], "a"), temporary=True),
        raises(ValueError), "duplicate hotkey warning not received")
    engine.remove_all_temporary()
    assert_that(
        calling(engine.create_phrase).with_args(folder, "test hotkey2",
                                                "contents", hotkey=(["<ctrl>"], "a"), temporary=True),
        not_(raises(ValueError)), "Doesn't ungrab hotkeys (duplicate hotkey warning received)")
