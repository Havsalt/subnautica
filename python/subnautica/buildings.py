from __future__ import annotations

from typing import TYPE_CHECKING

import colex
from charz import Sprite, Label, Hitbox, Vec2, load_texture, clamp

from .props import Interactable, Building

if TYPE_CHECKING:
    from .player import Player


class Ladder(Interactable, Sprite):
    _REACH = 2
    _REACH_FRACTION = 2 / 1
    z_index = 1
    color = colex.from_hex("#aaa9ad")
    transparency = " "
    centered = True
    texture = load_texture("lifepod/ladder.txt")
    parent: Lifepod

    def on_interact(self, interactor: Player) -> None:
        self.parent.on_exit()


# TODO: Crafting | Fabricatror (Medkit), Radio, O2, Power (Solar), Storage
class Lifepod(Interactable, Building, Sprite):
    _BOUNDARY = Hitbox(size=Vec2(19, 9), centered=True)
    _OPEN_CEILING = True
    _REACH = 15
    _REACH_FRACTION = 3 / 7
    _HIGHLIGHT_Z_INDEX = 0
    z_index = -2  # Increase when stepping into
    color = colex.BOLD + colex.WHITE
    centered = True
    texture = load_texture("lifepod/front.txt")
    entry_location = Vec2(0, -8)
    exit_location = Vec2(0, -7)
    # Used to track `Player`, for teleporting to exit location
    _curr_interactor: Player | None = None

    def __init__(self) -> None:
        self._name = Label(
            self,
            text="Lifepod",
            color=colex.ITALIC + colex.SLATE_GRAY,
            position=self.texture_size / -2,
        )
        self._name.position.y -= 3
        self._ladder = Ladder(self).as_visible(False)

    def on_interact(self, interactor: Player) -> None:
        # Reparent without moving
        location = interactor.global_position
        interactor.parent = self
        interactor.global_position = location
        # DEV
        interactor.global_position = self.global_position + self.entry_location
        # Change state and texture
        self._interactable = False
        # self.z_index = 2
        self.texture = load_texture("lifepod/inside.txt")
        self._curr_interactor = interactor
        self._ladder.show()

    # TODO: Improve
    def update(self, _delta: float) -> None:
        if not self._interactable:
            self.z_index = 0

    def on_exit(self) -> None:
        assert (
            self._curr_interactor is not None
        ), "current interactor is `None` when exited building"
        assert isinstance(self._curr_interactor.parent, Sprite), (
            f"{self._curr_interactor}.parent "
            f"({self._curr_interactor.parent}) is missing `Sprite` base"
        )
        # Unset parent of player
        self._curr_interactor.parent = None
        self._curr_interactor.global_position = (
            self.global_position + self.exit_location
        )
        # Unset player
        self._curr_interactor = None
        self._interactable = True
        # Transition to outside perspective
        self.z_index = self.__class__.z_index
        self.texture = load_texture("lifepod/front.txt")
        self._ladder.hide()
