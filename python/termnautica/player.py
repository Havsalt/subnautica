from math import floor
from typing import assert_never

import colex
import keyboard
from charz import Camera, Sprite, Collider, Hitbox, Vec2

from . import ui, ocean
from .props import Collectable, Interactable, Building
from .fabrication import Fabrication
from .particles import Bubble, Blood
from .item import ItemID, Stat, stats
from .utils import move_toward


type Action = str | int
type Count = int


ARROW_UP: int = 72
ARROW_DOWN: int = 80


class Player(Collider, Sprite):
    _GRAVITY: float = 0.91
    _JUMP_STRENGTH: float = 4
    _AIR_FRICTION: float = 0.7
    _WATER_FRICTION: float = 0.3
    _MAX_SPEED: Vec2 = Vec2(2, 2)
    _ACTIONS: tuple[Action, ...] = (  # Order is also precedence - First is highest
        ARROW_UP,  # NOTE: These 2 constants has to be checked before numeric strings
        ARROW_DOWN,
        "e",
        "1",
        "2",
        "3",
        "space",
        "tab",
        "enter",
        "j",
        "k",
    )
    position = Vec2(17, -18)
    hitbox = Hitbox(size=Vec2(5, 3), centered=True)
    z_index = 1
    color = colex.AQUA
    transparency = " "
    centered = True
    texture = [
        "  O",
        "/ | \\",
        " / \\",
    ]
    _y_speed: float = 0
    _current_action: Action | None = None
    _key_just_pressed: bool = False
    _current_interactable: Sprite | None = None

    def __init__(self) -> None:
        self.inventory = dict[ItemID, Count]()
        # NOTE: Current `Camera` has to be initialized before `Player.__init__` is called
        self._health_bar = ui.HealthBar(Camera.current)
        self._oxygen_bar = ui.OxygenBar(Camera.current)
        self._hunger_bar = ui.HungerBar(Camera.current)
        self._thirst_bar = ui.ThirstBar(Camera.current)
        ui.Inventory(Camera.current, inventory_ref=self.inventory)
        ui.HotbarE(Camera.current)
        ui.Hotbar1(Camera.current)
        ui.Hotbar2(Camera.current)
        ui.Hotbar3(Camera.current)
        self.crafting_gui = ui.Crafting(Camera.current)
        # DEV
        # self.inventory[ItemID.WATER_BOTTLE] = 2
        # self._thirst_bar.value = 50
        # self.inventory[ItemID.FRIED_FISH_NUGGET] = 2
        # self._hunger_bar.value = 50
        # self.inventory[ItemID.COD_SOUP] = 2
        # self.inventory[ItemID.BANDAGE] = 2
        # self._health_bar.value = 20

    def update(self, _delta: float) -> None:
        # Order of tasks
        self.handle_action_input()
        self.handle_gui()
        self.handle_movement()
        self.handle_interact_selection()
        self.handle_interact()
        self.handle_collect()
        self.handle_oxygen()
        self.handle_hunger()
        self.handle_thirst()
        # NOTE: Order of drinking, eating and healing is not visually correct
        self.handle_eating()
        self.handle_drinking()
        self.handle_healing()
        # Check if dead
        if self._health_bar.value == 0:
            self.on_death()

    def consume_item(self, item: ItemID, count: Count = 1) -> None:
        if item not in self.inventory:
            raise KeyError(
                f"Attempted removing {count} {item.name},"
                f" but {item.name} is not found in {self.inventory}"
            )
        elif count > self.inventory[item]:
            raise ValueError(
                f"Attempted to remove {count} {item.name},"
                f" but only has {self.inventory[item]} in {self.inventory}"
            )
        self.inventory[item] -= count

        for stat in Stat:
            if stat not in stats[item]:
                continue

            change = stats[item][stat]
            match stat:
                case Stat.EATABLE:
                    self._hunger_bar.value += change
                case Stat.DRINKABLE:
                    self._thirst_bar.value += change
                case Stat.HEALING:
                    self._health_bar.value += change
                case _:
                    assert_never(stat)

    def handle_eating(self) -> None:
        if not (self._current_action == "1" and self._key_just_pressed):
            return

        for item in self.inventory:
            if item in stats and Stat.EATABLE in stats[item]:
                self.consume_item(item)
                break

    def handle_drinking(self) -> None:
        if not (self._current_action == "2" and self._key_just_pressed):
            return

        for item in self.inventory:
            if item in stats and Stat.DRINKABLE in stats[item]:
                self.consume_item(item)
                break

    def handle_healing(self) -> None:
        if not (self._current_action == "3" and self._key_just_pressed):
            return

        for item in self.inventory:
            if item in stats and Stat.HEALING in stats[item]:
                self.consume_item(item)
                break

    def is_submerged(self) -> bool:
        self_height = self.global_position.y - self.texture_size.y / 2
        wave_height = ocean.Water.wave_height_at(self.global_position.x)
        return self_height - wave_height > 0

    def is_in_ocean(self):
        self_height = self.global_position.y + self.texture_size.y / 2 - 1
        wave_height = ocean.Water.wave_height_at(self.global_position.x)
        return self_height - wave_height > 0

    def is_in_building(self) -> bool:
        return isinstance(self.parent, Building)

    def is_colliding_with_ocean_floor(self) -> bool:
        # FIXME: Find out why it says `int | float` and not just `int` for `<Vec2i>.x`
        center = self.global_position
        if self.centered:
            center -= self.texture_size / 2
        for x_offset in range(int(self.texture_size.x)):
            for y_offset in range(int(self.texture_size.y)):
                global_point = (
                    floor(center.x + x_offset),
                    floor(center.y + y_offset),
                )
                if global_point in ocean.Floor.points:
                    return True
        return False

    def handle_action_input(self) -> None:
        if self._current_action is None:
            # Check for pressed
            for action in self._ACTIONS:
                if keyboard.is_pressed(action):
                    self._current_action = action
                    self._key_just_pressed = True
                    break
        elif self._key_just_pressed:
            # Deactivate "bool signal" after 1 single frame
            self._key_just_pressed = False
        elif not keyboard.is_pressed(self._current_action):
            # Release
            self._current_action = None

    def handle_gui(self) -> None:
        if not self._key_just_pressed:
            return
        if not isinstance(self._current_interactable, Fabrication):
            return
        if (
            self._current_action == "j"
            or self._current_action == ARROW_DOWN
            or (self._current_action == "tab" and not keyboard.is_pressed("shift"))
        ):
            self._current_interactable.attempt_select_next_recipe()
        elif (
            self._current_action == "k"
            or self._current_action == ARROW_UP
            or (self._current_action == "tab" and keyboard.is_pressed("shift"))
        ):
            self._current_interactable.attempt_select_previous_recipe()

    def handle_movement_in_building(self, velocity: Vec2) -> None:
        assert isinstance(self.parent, Building)
        # TODO: Check if is on floor first
        if self._current_action == "space" and self._key_just_pressed:
            self._y_speed = -self._JUMP_STRENGTH
        combined_velocity = Vec2(velocity.x, self._y_speed).clamped(
            -self._MAX_SPEED,
            self._MAX_SPEED,
        )
        self.parent.move_and_collide_inside(self, combined_velocity)
        # Apply friction
        self._y_speed = move_toward(self._y_speed, 0, self._AIR_FRICTION)

    def handle_movement(self) -> None:
        velocity = Vec2(
            keyboard.is_pressed("d") - keyboard.is_pressed("a"),
            keyboard.is_pressed("s") - keyboard.is_pressed("w"),
        )
        # Is in builindg movement
        if self.is_in_building():
            self.handle_movement_in_building(velocity)
            return
        # Is in air movement
        elif not self.is_in_ocean():
            self._y_speed += self._GRAVITY
        # Is in ocean movement
        combined_velocity = Vec2(velocity.x, velocity.y + self._y_speed).clamped(
            -self._MAX_SPEED,
            self._MAX_SPEED,
        )
        # NOTE: Order of x/y matter
        self.position.y += combined_velocity.y
        # Revert motion if ended up colliding
        if self.is_colliding_with_ocean_floor() or self.is_colliding():
            self.position.y -= combined_velocity.y
            self._y_speed = 0  # Hit ocean floor
        self.position.x += combined_velocity.x
        # Revert motion if ended up colliding
        if self.is_colliding_with_ocean_floor() or self.is_colliding():
            self.position.x -= combined_velocity.x
        # Apply friction
        friction = self._WATER_FRICTION if self.is_submerged() else self._AIR_FRICTION
        self._y_speed = move_toward(self._y_speed, 0, friction)

    def handle_oxygen(self) -> None:
        # Restore oxygen if inside a building with O2
        if (  # Is in building with oxygen
            isinstance(self.parent, Building) and self.parent.HAS_OXYGEN
        ):
            self._oxygen_bar.fill()
            return
        # Restore oxygen if above ocean waves
        if not self.is_submerged():
            if self._oxygen_bar.value != self._oxygen_bar.MAX_VALUE:
                self._oxygen_bar.fill()
            return
        # Decrease health if no oxygen, and spawn particles each tick
        if self._oxygen_bar.value == 0:
            self._health_bar.value -= 1
            Blood().with_global_position(
                x=self.global_position.x - 1,
                y=self.global_position.y - 1,
            )
            return
        # Decrease oxygen
        self._oxygen_bar.value -= 1 / 16
        raw_count = self._oxygen_bar.MAX_VALUE / self._oxygen_bar.MAX_CELL_COUNT
        # NOTE: Might be fragile logic, but works at least when
        #       MAX_VALUE = 300 and MAX_CELL_COUNT = 10
        if self._oxygen_bar.value % raw_count == 0:
            Bubble().with_global_position(
                x=self.global_position.x,
                y=self.global_position.y - 1,
            )

    def handle_hunger(self) -> None:
        self._hunger_bar.value -= 1 / 16
        if self._hunger_bar.value == 0:
            self._health_bar.value -= 1
            Blood().with_global_position(
                x=self.global_position.x - 1,
                y=self.global_position.y - 1,
            )

    def handle_thirst(self) -> None:
        self._thirst_bar.value -= 1 / 16
        if self._thirst_bar.value == 0:
            self._health_bar.value -= 1
            Blood().with_global_position(
                x=self.global_position.x - 1,
                y=self.global_position.y - 1,
            )

    def handle_interact_selection(self) -> None:
        proximite_interactables: list[tuple[float, Interactable]] = []
        global_point = self.global_position  # Store property value outside loop
        for node in Sprite.texture_instances.values():
            if (
                isinstance(node, Interactable)
                and node.interactable
                and (condition_and_dist := node.is_in_range_of(global_point))[0]
            ):  # I know this syntax might be a bit too much,
                # but know that it made it easier to split logic into mixin class
                proximite_interactables.append((condition_and_dist[1], node))

        # Highlight closest interactable - Using DSU
        if proximite_interactables:
            proximite_interactables.sort(key=lambda pair: pair[0])
            # Allow this because `Interactable` should always be used with `Sprite`
            if isinstance(self._current_interactable, Interactable):
                # Reset color to class color
                self._current_interactable.loose_focus()
                self._current_interactable.on_deselect(self)
            # Reverse color of current interactable
            first = proximite_interactables[0][1]
            assert isinstance(
                first,
                Sprite,
            ), f"{first.__class__} is missing `Sprite` base"
            self._current_interactable = first
            self._current_interactable.grab_focus()
            self._current_interactable.when_selected(self)
        # Or unselect last interactable that *was* in reach
        elif self._current_interactable is not None:
            assert isinstance(self._current_interactable, Interactable)
            self._current_interactable.loose_focus()
            self._current_interactable.on_deselect(self)
            self._current_interactable = None

    def handle_interact(self) -> None:
        if self._current_interactable is None:
            return
        assert isinstance(self._current_interactable, Interactable)
        # Trigger interaction function
        if self._key_just_pressed and (
            self._current_action == "e" or self._current_action == "enter"
        ):
            # TODO: Check for z_index change, so that it respects z_index change in on_interact
            self._current_interactable.on_interact(self)

    def handle_collect(self) -> None:
        if self._current_interactable is None:
            return
        if not isinstance(self._current_interactable, Collectable):
            return
        # Collect collectable that is selected
        # `self._current_interactable` is already in reach
        if self._key_just_pressed and (
            self._current_action == "e" or self._current_action == "enter"
        ):
            self._current_interactable.collect_into(self.inventory)
            self._current_interactable.queue_free()
            self._current_interactable = None

    # TODO: Implement
    def on_death(self) -> None:
        self.queue_free()
        if isinstance(self._current_interactable, Interactable):
            self._current_interactable.loose_focus()
        # Reset states
        self._current_interactable = None
        self._current_action = None
        self._key_just_pressed = False
