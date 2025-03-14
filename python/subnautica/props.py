"""Abstract classes defining properties for common functionality.

These classes are properties that can be used as "tags" when defining a node class.
Classes defined here will be used as `mixin components`.
They may also provide methods, either to be overwritten, or as base case.
"""

import pygame
import colex
from charz import Sprite, Hitbox, Vec2, clamp

from .item import Item

# NOTE: Add manually when a new tag/mixin is created
__all__ = [
    "Collectable",
    "Interactable",
    "Eatable",
    "Building",
]


class Collectable:
    NAME: str | None = None
    _SOUND_COLLECT: pygame.mixer.Sound | None = pygame.mixer.Sound(
        "assets/sounds/collect/default.wav"
    )

    def get_tags(self) -> list[type]:
        return [base for base in self.__class__.__mro__ if base.__name__ in __all__]

    def collect_into(self, inventory: dict[str, Item]) -> None:
        assert self.NAME is not None, f"{self}.name is `None`"

        if self.NAME in inventory:
            inventory[self.NAME].count += 1
            if self._SOUND_COLLECT is not None:
                self._SOUND_COLLECT.play()

        else:  # Insert new item with count of 1
            inventory[self.NAME] = Item(
                self.NAME,
                1,
                self.get_tags(),
            )


class Interactable:
    _REACH: float = 8  # Maximum length the interactor can be from the `Interactable`
    _REACH_FRACTION: float = 2 / 3  # Y-axis fraction, in linear transformation
    _REACH_CENTER: Vec2 = Vec2.ZERO  # Offset
    _HIGHLIGHT_Z_INDEX: int | None = None
    _interactable: bool = True  # Turn off when in use
    _last_z_index: int | None = None

    def grab_focus(self) -> None:
        assert isinstance(self, Sprite)
        self.color = colex.REVERSE + (self.__class__.color or colex.WHITE)
        if self._HIGHLIGHT_Z_INDEX is not None and self._last_z_index is None:
            self._last_z_index = self.z_index
            self.z_index = self._HIGHLIGHT_Z_INDEX

    def loose_focus(self) -> None:
        assert isinstance(self, Sprite)
        self.color = self.__class__.color
        if self._HIGHLIGHT_Z_INDEX is not None and self._last_z_index is not None:
            self.z_index = self._last_z_index
            self._last_z_index = None

    def is_in_range_of(self, global_point: Vec2) -> tuple[bool, float]:
        assert isinstance(self, Sprite)
        if not self._interactable:
            return (False, 0)
        reach_point = self.global_position + self._REACH_CENTER
        relative = global_point - reach_point
        relative.y /= self._REACH_FRACTION  # Apply linear transformation on Y-axis
        # NOTE: Using squared lengths for a bit more performance
        dist_squared = relative.length_squared()
        return (dist_squared <= self._REACH * self._REACH, dist_squared)

    def on_interact(self, interactor: Sprite) -> None: ...


# TODO: Make it `Consumable` instead, and have hunger, thirst and such be stat vars
class Eatable: ...


# TODO: Define building room bounding hitbox, that can be checked from `Player`
# TODO: Move building gravity of `Lifepod` into `Player`
class Building:
    HAS_OXYGEN: bool = True
    _BOUNDARY: Hitbox | None = None
    _OPEN_CEILING: bool = False

    def on_exit(self) -> None: ...  # Triggered when actor (`Player`) exits the building
    def move_and_collide_inside(self, node: Sprite, velocity: Vec2) -> None:
        assert isinstance(self, Sprite)
        if self._BOUNDARY is None:
            return

        if self._BOUNDARY.centered:
            start = -self._BOUNDARY.size / 2
            end = self._BOUNDARY.size / 2
        else:
            start = Vec2.ZERO
            end = self._BOUNDARY.size.copy()
        start += node.texture_size / 2
        end -= node.texture_size / 2

        # Apply gravity
        velocity.y += 1
        # Translate with snap
        if self._OPEN_CEILING:
            node.position.y = min(node.position.y + velocity.y, end.y)
        else:
            node.position.y = clamp(node.position.y + velocity.y, start.y, end.y)
        node.position.x = clamp(node.position.x + velocity.x, start.x, end.x)
