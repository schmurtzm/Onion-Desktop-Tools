"""Backup categories and their availability per card state (upstream rules)."""

from __future__ import annotations

import enum

from ..onion.detection import CardState


class Category(enum.Enum):
    ROMS = "roms"
    IMGS = "imgs"
    SAVES = "saves"
    RETROARCH = "retroarch"
    BIOS = "bios"
    ONION_CONFIG = "onion_config"

    @property
    def label(self) -> str:
        return {
            Category.ROMS: "ROMs",
            Category.IMGS: "Images (box art)",
            Category.SAVES: "Saves",
            Category.RETROARCH: "RetroArch configuration",
            Category.BIOS: "BIOS",
            Category.ONION_CONFIG: "Onion configuration flags",
        }[self]


ALL = tuple(Category)


def available_categories(state: CardState) -> tuple[Category, ...]:
    if state in (CardState.ONION, CardState.ONION_INSTALL_PENDING):
        return ALL
    if state is CardState.STOCK:
        return (Category.ROMS, Category.IMGS, Category.BIOS)
    return ()


PROFILES: dict[str, tuple[Category, ...]] = {
    "Complete": ALL,
    "Saves only": (Category.SAVES,),
    "Saves and configuration": (Category.SAVES, Category.RETROARCH, Category.ONION_CONFIG),
    "Games (ROMs + images)": (Category.ROMS, Category.IMGS),
}
