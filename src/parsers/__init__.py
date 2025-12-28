"""CSV parsers for DraftKings and FanDuel exports."""

from .platform_detector import detect_platform, is_draftkings, is_fanduel
from .base_parser import BaseParser
from .draftkings_parser import DraftKingsParser
from .fanduel_parser import FanDuelParser

__all__ = [
    'detect_platform',
    'is_draftkings',
    'is_fanduel',
    'BaseParser',
    'DraftKingsParser',
    'FanDuelParser',
]
