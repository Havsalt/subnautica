import random
from math import sin, pi as PI
from typing import ClassVar

import colex
from charz import Sprite, Vec2, Vec2i
from typing_extensions import Self

from . import fish, ores
from .kelp import Kelp
from .groupwise import groupwise


type Coordinate = tuple[int, int]


def randf(a: float, b: float, /) -> float:
    return random.random() * (b - a) + a


class OceanFloor(Sprite):
    z_index = -1
    color = colex.from_hex("#C2B280")
    texture = ["_"]


class OceanWater(Sprite):
    _WAVE_INTERVAL: float = 3 * 16  # frames
    _WAVE_DURATION: float = 3 * 16  # frames
    WAVE_AMPLITUDE: float = 2
    _WAVE_LENGTH: float = 100
    z_index = -1
    color = colex.MEDIUM_AQUAMARINE
    texture = ["~"]
    # _elapsed_time: ClassVar[float] = 0
    _wave_time_remaining: float = 0
    _rest_location: Vec2

    @classmethod
    def advance_wave_time(cls) -> None:  # Call from `App.update`
        cls._wave_time_remaining -= 1
        if cls._wave_time_remaining < 0:
            cls._wave_time_remaining = cls._WAVE_DURATION

    @classmethod
    def wave_height_at(cls, wave_origin_x: float) -> float:
        """Calculate wave height at global location

        Args:
            wave_origin (Vec2): global origin of wave

        Returns:
            float: global wave height
        """
        # Write in math symbols that I'm used to
        phi = wave_origin_x / cls._WAVE_LENGTH
        x = cls._wave_time_remaining / cls._WAVE_INTERVAL
        # Asin(cx + phi) + d
        return cls.WAVE_AMPLITUDE * sin(2 * PI * x + phi)

    def save_rest_location(self) -> Self:
        self._rest_location = self.global_position
        return self

    def update(self, _delta: float) -> None:
        # Asin(cx + phi) + d
        self.position.y = (
            self.wave_height_at(self._rest_location.x) + self._rest_location.y
        )

        # fraction = self._wave_time_remaining / self._WAVE_INTERVAL
        # phi = self._rest_location.x / self._WAVE_LENGTH
        # self.position.y = (
        #     self._WAVE_AMPLITUDE * sin(2 * PI * fraction + phi) + self._rest_location.y
        # )

        # if self._wave_time > 0:
        #     self._wave_time -= 1
        #     fraction = self._wave_time / self._WAVE_INTERVAL
        #     phi = self._rest_location.x / 100
        #     target_height = (
        #         self._rest_location.y
        #         + sin(2 * PI * fraction + phi) * self._WAVE_AMPLITUDE
        #     )
        #     self.position.y = clamp(
        #         self.position.y,
        #         target_height,
        #         0.40,
        #     )
        # elif self._elapse_time >= self._WAVE_INTERVAL:
        #     self._elapse_time -= self._WAVE_INTERVAL
        #     self._wave_time = self._WAVE_DURATION
        # else:
        #     self._elapse_time += 1
        #     self.position.y = clamp(
        #         self.position.y,
        #         self._rest_location.y,
        #         0.15,
        #     )


class Ocean(dict[Coordinate, OceanWater | OceanFloor]):
    _WIDTH: int = 500

    def __init__(self) -> None:
        self.generate_ocean_floor()
        self.generate_ocean_water()
        self.generate_fish()

    def generate_ocean_water(self) -> None:
        for x in range(self._WIDTH):
            (
                OceanWater()
                .with_position(
                    x=x - self._WIDTH // 2,
                    y=random.randint(0, 1),
                )
                .save_rest_location()
            )

    def generate_ocean_floor(self):
        height = 0
        points: list[Vec2i] = []
        for x_position in range(self._WIDTH):
            height += randf(-1, 1)
            point = Vec2i(
                x_position - self._WIDTH // 2,
                int(height) + 15,
            )
            points.append(point)
        # FIXME: Implement properly - Almost working
        for prev, curr, peak in groupwise(points, n=3):
            is_climbing = peak.y - curr.y < 0
            is_flatting = abs(peak.y - curr.y) < 0.8
            was_dropping = curr.y - prev.y > 0
            if is_flatting:
                ocean_floor = OceanFloor(position=curr)
            elif is_climbing and was_dropping:
                ocean_floor = OceanFloor(position=curr, texture=["V"])
            elif not is_climbing and not was_dropping:
                ocean_floor = OceanFloor(position=curr, texture=["A"])
            elif is_climbing:
                ocean_floor = OceanFloor(position=curr, texture=["/"])
            elif not is_climbing:
                ocean_floor = OceanFloor(position=curr, texture=["\\"])
            else:
                ocean_floor = OceanFloor(position=curr)
            # Make rock color if high up
            if curr.y < 10:
                ocean_floor.color = colex.GRAY
            # Store ref - For faster collision
            self[curr.to_tuple()] = ocean_floor
            # Generate kelp
            if curr.x < 0 and curr.y > 7:  # Kelp is 6 tall
                if random.randint(1, 100) > 90:
                    kelp = (
                        Kelp()
                        .with_position(Vec2(curr.x + 1, curr.y - 5))
                        .with_z_index(random.randint(0, 1))
                    )
                    if random.randint(0, 1):
                        kelp.is_on_last_frame = True
            else:  # Generate ores
                if random.randint(1, 100) > 92:
                    ore = random.choice([ores.Gold, ores.Copper, ores.Titanium])
                    ore(position=Vec2(curr.x - 1, curr.y))

    def generate_fish(self) -> None:
        for _ in range(2):
            for fish_type in [
                fish.SmallFish,
                fish.MediumFish,
                fish.LongFish,
                fish.WaterFish,
            ]:
                fish_type(
                    position=Vec2(
                        random.randint(-20, 20),
                        random.randint(2, 20),
                    )
                )
