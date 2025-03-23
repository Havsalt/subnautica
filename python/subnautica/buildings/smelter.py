import colex
from charz import Sprite, Vec2

from ..player import Player
from ..item import ItemID, Recipe
from ..props import Interactable
from ..fabrication import Fabrication


class Smelter(Fabrication, Interactable, Sprite):
    _REACH = 3
    _REACH_CENTER = Vec2(3, 0.5)
    _RECIPES = [
        Recipe(
            products={ItemID.COPPER_BAR: 2},
            idgredients={
                ItemID.COPPER_ORE: 2,
                ItemID.COAL_ORE: 1,
            },
        ),
        Recipe(
            products={ItemID.TITANIUM_BAR: 2},
            idgredients={
                ItemID.TITANIUM_ORE: 2,
                ItemID.COAL_ORE: 1,
            },
        ),
        Recipe(
            products={ItemID.GOLD_BAR: 2},
            idgredients={
                ItemID.GOLD_ORE: 2,
                ItemID.COAL_ORE: 1,
            },
        ),
    ]
    color = colex.ORANGE_RED
    texture = [
        "/^\\¨¨¨\\",
        "\\_/___/",
    ]
